"""EKF (T8.2, docs/design/T8.2_ekf.md): state [s, v, b, d_psi] from aligned IMU acceleration and GNSS."""
from __future__ import annotations

from typing import ClassVar

import numpy as np

from sim.contracts.estimation import Estimate, Measurement, Mode
from sim.estimators.alignment import Aligner, G
from sim.estimators.registry import register
from sim.world.road import RoadMap

R68_TO_AXIS = 1.5096  # h_acc is the radial 68% value; for a 2-D Gaussian R68 = 1.5096 * sigma_axis
_I4 = np.eye(4)
_H_GNSS = np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]])
_H_V = np.array([[0.0, 1.0, 0.0, 0.0]])


@register
class EkfEstimator:
    id = "ekf"
    label = "EKF (IMU + GNSS)"
    default_params: ClassVar[dict[str, float]] = {  # A31
        "bias_rw": 5e-4, "v_rw": 0.3, "init_bias_sigma": 0.1, "sigma_v": 0.2, "lateral_k": 3.0, "gate_chi2": 13.8,
        "speed_limit_factor": 1.3, "v_prior_sigma": 2.0, "accel_trust_sigma_b": 0.05,
        "initial_sigma_s": 50.0, "initial_sigma_v": 5.0, "gnss_timeout_s": 1.5, "recover_fixes": 3,
    }
    constraints: ClassVar[dict[str, dict[str, object]]] = {
        **{k: {"type": "float", "gt": 0} for k in default_params if k != "recover_fixes"},
        "recover_fixes": {"type": "int", "min": 1},
    }

    def reset(self, road: RoadMap, params: dict) -> None:
        for k, v in {**self.default_params, **params}.items():
            setattr(self, k, float(v))
        self.road = road
        self.aligner = Aligner(road)
        self.x = np.zeros(4)  # s, v, b, d_psi (remaining mount yaw error)
        self.P = np.diag([self.initial_sigma_s**2, self.initial_sigma_v**2, self.init_bias_sigma**2, 0.1**2])
        self._d_ready = False  # d_psi starts with the aligner's sigma_psi at the first aligned sample
        self._was_realigned = False
        self._limits = [(sl.from_s, sl.to_s, sl.kmh / 3.6) for sl in road.speed_limits]
        self._t_imu: float | None = None
        self._have_fix = False
        self._t_acc: float | None = None  # time of the last accepted fix
        self._fix_mode: Mode = "gnss"
        self._recover_left = 0

    # -- helpers ----------------------------------------------------------------------------------------------------
    def _limit(self, s: float) -> float | None:
        for lo, hi, v in self._limits:
            if lo <= s <= hi:
                return v
        return None

    def _clip(self) -> None:
        self.x[0] = min(max(self.x[0], 0.0), self.road.length_m)
        self.x[1] = max(self.x[1], 0.0)  # vehicles do not reverse in a tunnel

    def _kalman(self, h: np.ndarray, z: np.ndarray, r: np.ndarray, gate: float | None = None) -> bool:
        """Linear update (Joseph form); False if the chi-square gate rejects it."""
        y = z - h @ self.x
        s_mat = h @ self.P @ h.T + r
        if gate is not None and float(y @ np.linalg.solve(s_mat, y)) > gate:
            return False
        k = self.P @ h.T @ np.linalg.inv(s_mat)
        k[3, :] = 0.0  # consider state: d_psi's uncertainty is propagated, its mean is never updated (Joseph form holds for any gain)
        self.x = self.x + k @ y
        ikh = _I4 - k @ h
        self.P = ikh @ self.P @ ikh.T + k @ r @ k.T
        self._clip()
        return True

    # -- Estimator interface ----------------------------------------------------------------------------------------
    def update(self, m: Measurement) -> None:
        if m.kind == "imu":
            self._imu(m)
        elif m.kind == "gnss":
            self.aligner.process_gnss(m)
            self._gnss(m)

    def _reset_psi(self, sigma_psi: float) -> None:
        """d_psi = 0 with the aligner's sigma_psi; no correlation with the other states."""
        self.x[3] = 0.0
        self.P[3, :] = 0.0
        self.P[:, 3] = 0.0
        self.P[3, 3] = sigma_psi**2

    def _imu(self, m: Measurement) -> None:
        a = self.aligner.process_imu(m, float(self.x[0]), float(self.x[1]))  # the EKF's own position for the grade
        dt = 0.0 if self._t_imu is None else m.t - self._t_imu
        self._t_imu = m.t
        if dt <= 0.0:
            return
        if a.mount_changed:  # the constant offset may have changed with the mount
            self.P[2, 2] += (G * a.sigma_tilt) ** 2
        s, v, b, d = self.x
        if a.valid:
            al = self.aligner.active
            realigned = a.mode == "realigned"
            if (not self._d_ready or a.mount_changed or (self._was_realigned and not realigned)) and al is not None:
                self._reset_psi(al.sigma_psi)  # first aligned sample, a new mount, or a fresh calibration after a put-back
                d = 0.0
            self._d_ready, self._was_realigned = True, realigned
        # acceleration trust rule: with a poorly known offset, constant speed beats integrating acceleration. It applies
        # when no fix is current: with GNSS the offset can be re-learned, which needs the IMU prediction (in the
        # constant-velocity branch b is not coupled to v, so b could never come back below the threshold).
        gnss_current = self._t_acc is not None and m.t - self._t_acc <= self.gnss_timeout_s
        if a.valid and (gnss_current or np.sqrt(self.P[2, 2]) <= self.accel_trust_sigma_b):
            w = a.yaw_rate
            acc = a.a_long - b - d * v * w  # d_psi * a_lat is the yaw error's share of the measured a_long
            self.x = np.array([s + v * dt + 0.5 * acc * dt * dt, v + acc * dt, b, d])
            f = np.array([
                [1.0, dt - 0.5 * d * w * dt * dt, -0.5 * dt * dt, -0.5 * v * w * dt * dt],
                [0.0, 1.0 - d * w * dt, -dt, -v * w * dt],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ])
            g = np.array([0.5 * dt * dt, dt, 0.0, 0.0])
            q = self.aligner.sigma_base**2 * np.outer(g, g)  # sigma_psi * |v * w| is carried by d_psi, not counted twice
            q[2, 2] += self.bias_rw**2 * dt
        else:  # constant velocity, the driver's unknown acceleration as a velocity random walk
            self.x = np.array([s + v * dt, v, b, d])
            f = np.eye(4)
            f[0, 1] = dt
            q = np.zeros((4, 4))
            q[:2, :2] = self.v_rw**2 * np.array([[dt**3 / 3.0, dt**2 / 2.0], [dt**2 / 2.0, dt]])
        self.P = f @ self.P @ f.T + q
        self._clip()
        lim = self._limit(float(self.x[0]))
        if lim is not None and self.x[1] > self.speed_limit_factor * lim:  # weak speed prior
            self._kalman(_H_V, np.array([lim]), np.array([[self.v_prior_sigma**2]]))

    def _gnss(self, m: Measurement) -> None:
        d = m.data
        s_meas = float(self.road.project(d["x"], d["y"]))
        sig_s = float(d["h_acc"]) / R68_TO_AXIS
        speed_acc = d.get("speed_acc")
        sig_v = float(speed_acc) if speed_acc is not None and speed_acc > 0 else self.sigma_v
        pos = self.road.at(s_meas)
        if np.hypot(d["x"] - pos["x"], d["y"] - pos["y"]) > self.lateral_k * sig_s:
            return  # far off the single-lane road: a broken fix
        z, r = np.array([s_meas, float(d["speed"])]), np.diag([sig_s**2, sig_v**2])
        if not self._have_fix:
            self.x = np.array([s_meas, z[1], 0.0, 0.0])
            self.P = np.diag([r[0, 0], r[1, 1], self.init_bias_sigma**2, 0.1**2])
            self._have_fix = True
        elif not self._kalman(_H_GNSS, z, r, gate=self.gate_chi2):
            return
        if self._t_acc is not None and m.t - self._t_acc > self.gnss_timeout_s:
            self._recover_left = int(self.recover_fixes)  # first fix after an outage
        self._fix_mode = "recovering" if self._recover_left > 0 else "gnss"
        self._recover_left = max(self._recover_left - 1, 0)
        self._t_acc = m.t

    def estimate(self, t: float) -> Estimate:
        mode: Mode = "dead_reckoning"
        if self._t_acc is not None and t - self._t_acc <= self.gnss_timeout_s:
            mode = self._fix_mode
        return Estimate(t=t, s=float(self.x[0]), v=float(self.x[1]), sigma_s=float(np.sqrt(self.P[0, 0])),
                        sigma_v=float(np.sqrt(self.P[1, 1])), mode=mode)
