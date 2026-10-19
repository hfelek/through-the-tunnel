"""Shared preprocessing (T8.1): mount alignment, longitudinal acceleration, yaw rate, handling detection.

Sees only measurements and the map. One `Aligner` per estimator instance; the estimator passes its own
`s_est` and `v_est` with every IMU sample (needed for the map grade and curvature).

Frames: the phone frame is the Android one (CONTRACTS 3.1). `M` has the vehicle axes as rows, expressed in phone
coordinates: v_vehicle = M v_phone, rows (f, l, u) = (forward, left, up).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from itertools import pairwise
from typing import ClassVar, Literal

import numpy as np

from sim.contracts.estimation import Measurement
from sim.geometry.so3 import exp_so3
from sim.world.road import RoadMap

G = 9.80665  # standard gravity, m/s^2
AlignMode = Literal["uncalibrated", "aligned", "in_hand", "realigned"]
_EPS_PP = 1e-6  # sum |p_k|^2 below this: the yaw is not observable yet (no speed change or turn seen)


@dataclass(slots=True)
class AlignedSample:
    """`a_long` / `yaw_rate` are 0 and `sigma_a_long` is inf whenever `valid` is False."""

    t: float
    a_long: float
    sigma_a_long: float
    yaw_rate: float
    valid: bool
    mode: AlignMode


@dataclass(slots=True)
class _Alignment:
    f: np.ndarray
    l: np.ndarray
    u: np.ndarray
    sigma_psi: float
    source: Literal["calibrated", "realigned"]

    @property
    def m(self) -> np.ndarray:
        return np.stack([self.f, self.l, self.u])


def _unit(v: np.ndarray) -> np.ndarray:
    return v / np.linalg.norm(v)


def _rz(a: float) -> np.ndarray:
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def _ry(a: float) -> np.ndarray:
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


class Aligner:
    default_params: ClassVar[dict[str, float]] = {
        "sigma_base": 0.3,  # m/s^2, A28
        "gnss_current_s": 1.5,
        "min_cal_s": 20.0,
        "flat_grade": 0.005,
        "flat_window_m": 50.0,
        "straight_curvature": 1e-4,
        "hand_start_rad_s": 0.15,  # A29
        "hand_start_s": 0.2,
        "hand_end_rad_s": 0.03,
        "hand_end_s": 1.0,
        "gyro_avg_s": 0.2,  # moving average before thresholding: vibration noise is ~1.3 sigma below the end threshold raw
        "stage_s": 0.3,  # calibration samples wait this long, so a hand movement cannot contaminate the sums
        "integ_lead_s": 0.5,  # integrate the hand rotation from this long before the detected start
        "gravity_avg_s": 2.0,
        "realign_speed_rel_sigma": 0.05,  # speed error enters the vehicle yaw change through the map curvature
        "gyro_bias_rw": 1e-4,  # rad/s/sqrt(s): bias drift while integrating through the hand event
    }
    constraints: ClassVar[dict[str, dict[str, object]]] = {k: {"type": "float", "gt": 0} for k in default_params}

    def __init__(self, road_map: RoadMap, params: dict | None = None) -> None:
        p = {**self.default_params, **(params or {})}
        for k, v in p.items():
            setattr(self, k, float(v))
        self._road = road_map
        line = road_map.line
        self._step = float(line.s[1] - line.s[0])
        self._grade, self._curv = line.grade, line.curvature
        w = max(1, round(self.flat_window_m / self._step))
        wide = np.lib.stride_tricks.sliding_window_view(np.pad(np.abs(self._grade), (w, w), mode="edge"), 2 * w + 1)
        self._flat = wide.max(axis=1) < self.flat_grade
        self._straight = self._flat & (np.abs(self._curv) < self.straight_curvature)
        self.b_g: np.ndarray | None = None
        self.active: _Alignment | None = None
        self.in_hand = False
        self.hand_log: list[list[float | None]] = []  # [start_t, end_t or None] per detected event
        self._fix: tuple[float, float, float] | None = None  # t, s, v of the last GNSS fix
        self._buf: list[tuple[float, np.ndarray, np.ndarray]] = []  # IMU samples since the last fix
        self._buf_bad = False
        self._reset_mount_sums()
        self._n_str, self._sum_g_str = 0.0, np.zeros(3)  # gyro bias survives a mount change
        self._stage: deque = deque()
        self._t_prev: float | None = None
        self._gavg: deque = deque()
        self._gavg_sum = np.zeros(3)
        self._ring: deque = deque()  # (t, gyro, v_est * curvature, s_est) for the pre-start integration
        self._exceed_t: float | None = None
        self._calm_t: float | None = None
        self._pre: _Alignment | None = None
        self._grav: dict | None = None

    # -- map lookups ------------------------------------------------------------------------------------------------
    def _i(self, s: float) -> int:
        return int(min(max(s / self._step, 0.0), len(self._grade) - 1))

    @property
    def mode(self) -> AlignMode:
        if self.in_hand:
            return "in_hand"
        if self.active is None:
            return "uncalibrated"
        return "realigned" if self.active.source == "realigned" else "aligned"

    # -- calibration ------------------------------------------------------------------------------------------------
    def _reset_mount_sums(self) -> None:
        self._n_flat, self._sum_a_flat = 0.0, np.zeros(3)
        self._recs: list[tuple] = []  # per GNSS interval: A, W, V, dv, grade term, flat, span

    def process_gnss(self, m: Measurement) -> None:
        d = m.data
        s, v = float(self._road.project(d["x"], d["y"])), float(d["speed"])
        prev = self._fix
        clean = not self._buf_bad and not self.in_hand and self._exceed_t is None
        if prev is not None and clean and 0 < m.t - prev[0] <= self.gnss_current_s:
            self._close_interval(prev, (m.t, s, v))
        self._fix = (m.t, s, v)
        self._buf, self._buf_bad = [], False

    def _close_interval(self, f0: tuple, f1: tuple) -> None:
        (t0, s0, v0), (t1, s1, v1) = f0, f1
        rows = [r for r in self._buf if t0 < r[0] <= t1]
        if not rows or rows[0][0] - t0 > 0.1:
            return
        ts = np.array([r[0] for r in rows])
        a, g = np.array([r[1] for r in rows]), np.array([r[2] for r in rows])
        w = np.diff(np.concatenate(([t0], ts)))
        if ts[-1] < t1:  # hold the last sample to the fix time
            a, g, w, ts = np.vstack([a, a[-1]]), np.vstack([g, g[-1]]), np.append(w, t1 - ts[-1]), np.append(ts, t1)
        span = t1 - t0
        vv = v0 + (v1 - v0) * (ts - t0) / span
        i = self._i(0.5 * (s0 + s1))
        self._recs.append((
            (w[:, None] * a).sum(0), ((w * vv)[:, None] * g).sum(0), float((w * vv).sum()), v1 - v0,
            G * np.sin(np.arctan(self._grade[i])) * span, bool(self._flat[i]), span,
        ))
        self._try_update()

    def _basis(self, u: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        axis = np.eye(3)[int(np.argmin(np.abs(u)))]
        e1 = _unit(axis - (axis @ u) * u)
        return e1, np.cross(u, e1)

    def _fit(self, u: np.ndarray, b: np.ndarray) -> tuple[float, np.ndarray, np.ndarray, float] | None:
        """Procrustes yaw psi about u: returns psi, p_k (N, 2), m_k (N, 2) and sum |p|^2."""
        e1, e2 = self._basis(u)
        a = np.array([r[0] for r in self._recs])
        wv = np.array([r[1] for r in self._recs])
        vi = np.array([r[2] for r in self._recs])
        dv, gr = np.array([r[3] for r in self._recs]), np.array([r[4] for r in self._recs])
        m = np.stack([a @ e1, a @ e2], axis=1)
        p = np.stack([dv + gr, wv @ u - (b @ u) * vi], axis=1)
        pp = float(np.sum(p * p))
        if pp < _EPS_PP:
            return None
        psi = float(np.arctan2(np.sum(p[:, 0] * m[:, 1] - p[:, 1] * m[:, 0]), np.sum(p[:, 0] * m[:, 0] + p[:, 1] * m[:, 1])))
        return psi, p, m, pp

    def _solve(self) -> _Alignment | None:
        if self._n_flat < self.min_cal_s or self._n_str < self.min_cal_s or len(self._recs) < 3:
            return None
        if sum(r[6] for r in self._recs) < self.min_cal_s:
            return None
        b = self._sum_g_str / self._n_str
        u = _unit(self._sum_a_flat)
        fit = self._fit(u, b)
        if fit is None:
            return None
        # refine u once the forward axis is known: remove the forward and lateral kinematic acceleration (flat intervals)
        psi = fit[0]
        e1, e2 = self._basis(u)
        f = np.cos(psi) * e1 + np.sin(psi) * e2
        lat = np.cross(u, f)
        flat = [r for r in self._recs if r[5]]
        if flat:
            u1 = _unit(sum(r[0] - f * (r[3] + r[4]) - lat * (r[1] @ u - (b @ u) * r[2]) for r in flat))
            fit1 = self._fit(u1, b)
            if fit1 is not None:
                u, fit = u1, fit1
        psi, p, m, pp = fit
        e1, e2 = self._basis(u)
        f = np.cos(psi) * e1 + np.sin(psi) * e2
        c, s = np.cos(psi), np.sin(psi)
        resid = m - np.stack([p[:, 0] * c - p[:, 1] * s, p[:, 0] * s + p[:, 1] * c], axis=1)
        sigma = float(np.sqrt(np.sum(resid * resid) / (len(p) - 1)) / np.sqrt(pp))
        return _Alignment(f=f, l=np.cross(u, f), u=u, sigma_psi=sigma, source="calibrated")

    def _try_update(self) -> None:
        cal = self._solve()
        if cal is None:
            return
        if self.active is None or self.active.source == "calibrated" or cal.sigma_psi < self.active.sigma_psi:
            self.active = cal

    # -- handling ---------------------------------------------------------------------------------------------------
    def _begin_hand(self, b: np.ndarray) -> None:
        self.in_hand = True
        start = self._exceed_t
        self.hand_log.append([start, None])
        self._exceed_t = self._calm_t = None
        self._pre, self._grav = self.active, None
        self._reset_mount_sums()  # the mount is about to change: calibration data so far describes the old one
        self._stage.clear()
        self._R, self._yaw, self._habs, self._t_int0, self._p0 = np.eye(3), 0.0, 0.0, None, 0.0
        rows = [r for r in self._ring if r[0] >= start - self.integ_lead_s]
        for prev, cur in pairwise(rows):
            self._integrate(prev, cur, b)

    def _integrate(self, prev: tuple, cur: tuple, b: np.ndarray) -> None:
        """Hold-last integration of the phone rotation and the map yaw change over [prev.t, cur.t]."""
        if self._t_int0 is None:
            self._t_int0, self._p0 = prev[0], float(np.arctan(self._grade[self._i(prev[3])]))
        dt = cur[0] - prev[0]
        self._R = self._R @ exp_so3((prev[1] - b) * dt)
        self._yaw += prev[2] * dt
        self._habs += abs(prev[2]) * dt

    def _end_hand(self, t: float, s_est: float) -> None:
        """Re-align after put-back.

        The phone's world orientation is R_wp = Rv M (Rv: vehicle -> world, M: phone -> vehicle). The integrated gyro
        gives dR_P = R_wp0^T R_wp1 = M0^T (Rv0^T Rv1) M1, hence M1 = dRv^T M0 dR_P, with dRv the vehicle's own rotation
        over the event: Rv = Rz(yaw) Ry(-pitch) gives dRv = Ry(p0) Rz(dyaw) Ry(-p1), dyaw = integral of v * curvature,
        p = atan(map grade).
        """
        self.in_hand = False
        self.hand_log[-1][1] = t
        pre = self._pre
        if pre is None:
            self.active = None
            return
        d_rv = _ry(self._p0) @ _rz(self._yaw) @ _ry(-float(np.arctan(self._grade[self._i(s_est)])))
        m1 = d_rv.T @ pre.m @ self._R
        dur = t - self._t_int0
        sigma = float(np.hypot.reduce([pre.sigma_psi, self.realign_speed_rel_sigma * self._habs,
                                       self.gyro_bias_rw * dur**1.5 / np.sqrt(3.0)]))
        self.active = _Alignment(f=m1[0], l=m1[1], u=m1[2], sigma_psi=sigma, source="realigned")
        self._grav = {"t0": t, "n": 0, "a": np.zeros(3), "al": 0.0, "gs": 0.0, "v0": None, "v1": 0.0}

    def _gravity_step(self, t: float, a: np.ndarray, s_est: float, v_est: float, vk: float) -> None:
        """Pitch / roll refinement from gravity, over `gravity_avg_s` after put-back; yaw stays from the gyro."""
        gr = self._grav
        if gr["v0"] is None:
            gr["v0"] = v_est
        gr["n"] += 1
        gr["a"] += a
        gr["al"] += v_est * vk
        gr["gs"] += G * np.sin(np.arctan(self._grade[self._i(s_est)]))
        gr["v1"] = v_est
        if t - gr["t0"] < self.gravity_avg_s:
            return
        self._grav, al = None, self.active
        n, span = gr["n"], t - gr["t0"]
        u = _unit(gr["a"] / n - al.f * ((gr["v1"] - gr["v0"]) / span + gr["gs"] / n) - al.l * gr["al"] / n)
        if np.degrees(np.arccos(np.clip(u @ al.u, -1.0, 1.0))) < 15.0:
            f = _unit(al.f - (al.f @ u) * u)
            self.active = _Alignment(f=f, l=np.cross(u, f), u=u, sigma_psi=al.sigma_psi, source="realigned")

    # -- IMU --------------------------------------------------------------------------------------------------------
    def process_imu(self, m: Measurement, s_est: float, v_est: float) -> AlignedSample:
        t, d = m.t, m.data
        a = np.array([d["ax"], d["ay"], d["az"]])
        g = np.array([d["gx"], d["gy"], d["gz"]])
        dt = min(t - self._t_prev, 0.1) if self._t_prev is not None else 0.0
        b = self.b_g if self.b_g is not None else np.zeros(3)
        vk = v_est * self._curv[self._i(s_est)]  # expected vehicle yaw rate from the map
        cur = (t, g, vk, s_est)
        self._ring.append(cur)
        while self._ring[0][0] < t - 1.0:
            self._ring.popleft()
        if self.in_hand and len(self._ring) > 1:
            self._integrate(self._ring[-2], cur, b)

        # smoothed gyro for the thresholds
        self._gavg.append((t, g))
        self._gavg_sum += g
        while self._gavg[0][0] < t - self.gyro_avg_s:
            self._gavg_sum -= self._gavg.popleft()[1]
        w = self._gavg_sum / len(self._gavg) - b
        score = float(np.linalg.norm(w - vk * self.active.u)) if self.active is not None else max(float(np.linalg.norm(w)) - abs(vk), 0.0)
        if not self.in_hand:
            if score > self.hand_start_rad_s:
                self._exceed_t = t if self._exceed_t is None else self._exceed_t
                if t - self._exceed_t > self.hand_start_s:
                    self._begin_hand(b)
            else:
                self._exceed_t = None
        elif score < self.hand_end_rad_s:
            self._calm_t = t if self._calm_t is None else self._calm_t
            if t - self._calm_t >= self.hand_end_s:
                self._end_hand(t, s_est)
        else:
            self._calm_t = None

        # calibration data (only with current GNSS, never near a hand movement)
        eligible = self._fix is not None and t - self._fix[0] <= self.gnss_current_s and not self.in_hand and self._exceed_t is None
        if self._fix is not None and t > self._fix[0]:
            self._buf.append((t, a, g))
            self._buf_bad |= self.in_hand or self._exceed_t is not None
        if eligible and dt > 0:
            i = self._i(self._fix[1] + self._fix[2] * (t - self._fix[0]))
            self._stage.append((t, dt, a, g, bool(self._flat[i]), bool(self._straight[i])))
        while self._stage and t - self._stage[0][0] >= self.stage_s:
            _, sdt, sa, sg, flat, straight = self._stage.popleft()
            if flat:
                self._n_flat += sdt
                self._sum_a_flat += sdt * sa
            if straight:
                self._n_str += sdt
                self._sum_g_str += sdt * sg
        if self._n_str >= self.min_cal_s:
            self.b_g = self._sum_g_str / self._n_str
        if self._grav is not None and not self.in_hand and self.active is not None:
            self._gravity_step(t, a, s_est, v_est, vk)
        self._t_prev = t

        al = self.active
        if self.in_hand or al is None:
            return AlignedSample(t, 0.0, float("inf"), 0.0, False, self.mode)
        yaw_rate = float((g - b) @ al.u)
        a_long = float(al.f @ a - G * np.sin(np.arctan(self._grade[self._i(s_est)])))
        sigma = float(np.hypot(self.sigma_base, al.sigma_psi * abs(v_est * yaw_rate)))
        return AlignedSample(t, a_long, sigma, yaw_rate, True, self.mode)
