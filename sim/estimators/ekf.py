"""EKF (T8.2, docs/design/T8.2_ekf.md): state [s, v, b, d_psi] from aligned IMU acceleration and GNSS."""
from __future__ import annotations

from typing import ClassVar

import numpy as np

from sim.contracts.estimation import Estimate, Measurement, Mode
from sim.estimators.alignment import Aligner, G
from sim.estimators.beacon_peak import PeakDetector
from sim.estimators.registry import register
from sim.estimators.stationary import StationaryDetector
from sim.world.road import RoadMap

R68_TO_AXIS = 1.5096  # h_acc is the radial 68% value; for a 2-D Gaussian R68 = 1.5096 * sigma_axis
_I4 = np.eye(4)
_H_GNSS = np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]])
_H_S = np.array([[1.0, 0.0, 0.0, 0.0]])
_H_V = np.array([[0.0, 1.0, 0.0, 0.0]])
_H_B = np.array([[0.0, 0.0, 1.0, 0.0]])
ZUPT_PERIOD_S = 0.1  # zero-velocity update rate while stationary (10 Hz)
BEACON_GATE_CHI2 = 10.8  # chi-square, 1 dof, 99.9% (the beacon measures s only)
BIAS_PERIOD_S = 1.0  # bias update rate while stationary


@register
class EkfEstimator:
    id = "ekf"
    label = "EKF"
    default_params: ClassVar[dict[str, float]] = {  # A31
        "bias_rw": 5e-4, "v_rw": 0.3, "init_bias_sigma": 0.1, "sigma_v": 0.2, "lateral_k": 3.0, "gate_chi2": 13.8,
        "speed_limit_factor": 1.3, "v_prior_sigma": 2.0, "accel_trust_sigma_b": 0.05,
        "initial_sigma_s": 50.0, "initial_sigma_v": 5.0, "gnss_timeout_s": 1.5, "recover_fixes": 3,
        "gate_reset_n": 5, "display_k": 0.5, "display_max_catchup": 10.0,  # T8.6, A31
        "beacon_min_dbm": -85.0, "beacon_drop_db": 3.0, "beacon_sigma": 5.0,  # T8.5, A33
    }
    param_info: ClassVar[dict[str, dict[str, str]]] = {  # display metadata for the UI (T7.9-CR1); A31 = EKF tuning, A33 = beacons
        "bias_rw": {"label": "Accelerometer bias drift", "unit": "m/s²/√s", "description": "How fast the accelerometer bias may drift (process noise on the bias). Raising it relearns the bias faster but makes the estimate noisier (A31)."},
        "v_rw": {"label": "Speed noise without accelerometer", "unit": "m/s/√s", "description": "Process noise on speed when the accelerometer is not used: the driver's unknown acceleration. Raising it widens the uncertainty and makes the filter follow GNSS speed more closely (A31)."},
        "init_bias_sigma": {"label": "Initial accelerometer bias uncertainty", "unit": "m/s²", "description": "Uncertainty of the accelerometer bias at the start and at the first fix. Raising it lets the first fixes correct the bias more strongly (A31)."},
        "sigma_v": {"label": "Speed noise of a fix", "unit": "m/s", "description": "Speed noise assumed for a GNSS fix that reports no speed accuracy (A31)."},
        "lateral_k": {"label": "Off-road limit", "unit": "× sigma", "description": "A fix farther from the road than this many sigma (h_acc / 1.5096) is dropped as broken (A31)."},
        "gate_chi2": {"label": "GNSS gate", "unit": "chi-square", "description": "Chi-square limit (2 degrees of freedom, 99.9%) on a fix's position and speed innovation. A fix above it is rejected; raising it accepts more outliers (A31)."},
        "speed_limit_factor": {"label": "Speed-limit factor", "unit": "×", "description": "When the estimated speed exceeds this factor times the road's speed limit, a weak speed-limit measurement pulls it down (A31)."},
        "v_prior_sigma": {"label": "Speed-limit pull", "unit": "m/s", "description": "Standard deviation of that speed-limit measurement. Larger means a weaker pull (A31)."},
        "accel_trust_sigma_b": {"label": "Accelerometer trust limit", "unit": "m/s²", "description": "Without a current fix, the accelerometer is integrated only while the bias uncertainty is below this; otherwise the speed is held constant (A31)."},
        "initial_sigma_s": {"label": "Initial position uncertainty", "unit": "m", "description": "Position uncertainty before the first fix (A31)."},
        "initial_sigma_v": {"label": "Initial speed uncertainty", "unit": "m/s", "description": "Speed uncertainty before the first fix (A31)."},
        "gnss_timeout_s": {"label": "GNSS timeout", "unit": "s", "description": "Time after the last accepted fix when the fix is no longer current. The filter then reports dead reckoning, and the accelerometer trust rule applies (A31)."},
        "recover_fixes": {"label": "Fixes marked recovering", "unit": "count", "description": "Number of fixes after an outage that carry the mode 'recovering'. A label only; the update is the same (A31)."},
        "gate_reset_n": {"label": "Gate reset count", "unit": "count", "description": "After this many on-road fixes in a row rejected by the gate, position and speed are reset from the fix (T8.6, A31)."},
        "display_k": {"label": "Display catch-up gain", "unit": "1/s", "description": "Share of the gap between the displayed position and the estimate that the display closes per second. Affects the display only (T8.6, A31)."},
        "display_max_catchup": {"label": "Display speed limit", "unit": "m/s", "description": "The displayed position never moves faster than the speed plus this. Affects the display only (T8.6, A31)."},
        "beacon_min_dbm": {"label": "Beacon detection level", "unit": "dBm", "description": "A beacon pass is recognised only while the 1 s average signal is above this level (T8.5, A33)."},
        "beacon_drop_db": {"label": "Beacon peak drop", "unit": "dB", "description": "A pass ends, and its peak time is fixed, when the signal falls this far below its maximum (T8.5, A33)."},
        "beacon_sigma": {"label": "Beacon position noise", "unit": "m", "description": "Position error of the beacon peak time alone. The update also adds the speed uncertainty times the detection age on top of this (T8.5, A33)."},
    }
    constraints: ClassVar[dict[str, dict[str, object]]] = {
        **{k: {"type": "float", "gt": 0} for k in default_params
           if k not in ("recover_fixes", "gate_reset_n", "beacon_min_dbm")},
        "beacon_min_dbm": {"type": "float", "min": -100.0, "max": -40.0},  # RSSI of a nearby beacon, dBm
        "recover_fixes": {"type": "int", "min": 1},
        "gate_reset_n": {"type": "int", "min": 1},
    }
    zupt = False  # the subclass EkfZuptEstimator turns the stationary updates on

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
        self._gate_streak = 0  # consecutive on-road fixes rejected by the chi-square gate (T8.6)
        self.gate_resets = 0  # counter, for inspection
        self.aligned = None
        self._display_s = 0.0  # the position shown on screen, never moves backwards (T8.6)
        self._beacon_s = dict(road.beacons)  # map knowledge: beacon id -> s (T8.5)
        self._peaks: dict[str, PeakDetector] = {}
        self.beacon_updates = 0  # accepted beacon updates, for inspection
        if self.zupt:
            self._detector = StationaryDetector(self.zupt_acc_std, self.zupt_gyro_std)
            self._next_zupt = 0.0
            self._bias_t0: float | None = None
            self._bias_sum, self._bias_n = 0.0, 0
            self.zupt_applied = self.zupt_gated = self.bias_updates = 0  # counters, for inspection

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
            self._beacon_silence(m.t)
        elif m.kind == "ble":
            self._ble(m)
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
        self.aligned = a  # kept for the particle filter, which needs the yaw rate (T8.4)
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
        self._advance_display(dt)
        lim = self._limit(float(self.x[0]))
        if lim is not None and self.x[1] > self.speed_limit_factor * lim:  # weak speed prior
            self._kalman(_H_V, np.array([lim]), np.array([[self.v_prior_sigma**2]]))
        if self.zupt:
            self._stationary_updates(m, a.valid, a.a_long)

    def _advance_display(self, dt: float) -> None:
        """display_s follows the speed and is pulled to s at display_k per second; rate in [0, v + max_catchup] (T8.6, A31)."""
        v = float(self.x[1])
        rate = v + self.display_k * (float(self.x[0]) - self._display_s)
        # lower bound 0: never backwards, so a backward jump of s makes the display hold until the vehicle catches up;
        # upper bound: a forward jump is absorbed within a few seconds without a visible leap
        self._display_s += min(max(rate, 0.0), v + self.display_max_catchup) * dt
        self._display_s = min(self._display_s, self.road.length_m)

    def _reinit_from_fix(self, z: np.ndarray, r: np.ndarray) -> None:
        """Gate safeguard: the filter is overconfident, so trust the fix. s and v from the fix, b and d_psi kept (T8.6)."""
        self.x[0], self.x[1] = z
        self.P[:2, :] = 0.0  # no correlation left between the new (s, v) and the kept states
        self.P[:, :2] = 0.0
        self.P[:2, :2] = r
        self._clip()
        self.gate_resets += 1

    def _speed_not_zero(self) -> bool:
        """Same chi-square test as the v = 0 gate: the EKF's speed and uncertainty cannot be explained by standing still."""
        return self.x[1] ** 2 / (self.P[1, 1] + self.zupt_v_sigma**2) > self.zupt_gate_chi2

    def _stationary_updates(self, m: Measurement, aligned: bool, a_long: float) -> None:
        """While the detector says stationary: v = 0 at 10 Hz (gated) and the mean a_long as a bias measurement at 1 Hz."""
        d = m.data
        if not self._detector.update(m.t, d["ax"], d["ay"], d["az"], d["gx"], d["gy"], d["gz"]):
            self._bias_t0, self._bias_sum, self._bias_n = None, 0.0, 0  # leaving a stop: restart the bias window
            return
        if m.t >= self._next_zupt:
            self._next_zupt = m.t + ZUPT_PERIOD_S
            # gate: if the EKF's own speed and uncertainty cannot be explained by v = 0 (slow crawl, false detection), skip
            ok = self._kalman(_H_V, np.array([0.0]), np.array([[self.zupt_v_sigma**2]]), gate=self.zupt_gate_chi2)
            self.zupt_applied, self.zupt_gated = self.zupt_applied + ok, self.zupt_gated + (not ok)
        if self._bias_t0 is None:
            self._bias_t0 = m.t
        if aligned:
            self._bias_sum, self._bias_n = self._bias_sum + a_long, self._bias_n + 1
        if m.t - self._bias_t0 >= BIAS_PERIOD_S and self._bias_n > 0:
            if self._speed_not_zero():  # the car is pulling away: the detector lags, so this window holds real acceleration
                self._bias_t0, self._bias_sum, self._bias_n = m.t, 0.0, 0
                return
            # standing still the true acceleration is 0, so the mean of a_long measures the offset b (sigma_base is per sample)
            r = self.aligner.sigma_base**2 / self._bias_n
            self._kalman(_H_B, np.array([self._bias_sum / self._bias_n]), np.array([[r]]))
            self.bias_updates += 1
            self._bias_t0, self._bias_sum, self._bias_n = m.t, 0.0, 0

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
            self._display_s = float(self.x[0])
        elif not self._kalman(_H_GNSS, z, r, gate=self.gate_chi2):
            self._gate_streak += 1
            if self._gate_streak < self.gate_reset_n:
                return
            self._reinit_from_fix(z, r)  # n fixes in a row on the road but far from the estimate: the estimate is wrong
        self._gate_streak = 0
        if self._t_acc is not None and m.t - self._t_acc > self.gnss_timeout_s:
            self._recover_left = int(self.recover_fixes)  # first fix after an outage
        self._fix_mode = "recovering" if self._recover_left > 0 else "gnss"
        self._recover_left = max(self._recover_left - 1, 0)
        self._t_acc = m.t

    def _ble(self, m: Measurement) -> None:
        bid = m.data["beacon_id"]
        if bid not in self._beacon_s:
            return  # a beacon the map does not know
        det = self._peaks.setdefault(bid, PeakDetector(self.beacon_min_dbm, self.beacon_drop_db))
        t_peak = det.add(m.t, float(m.data["rssi"]))
        if t_peak is not None:
            self._beacon_update(bid, m.t, t_peak)

    def _beacon_silence(self, t: float) -> None:
        """Check every IMU step: a beacon that went quiet is detected without waiting for another packet."""
        for bid, det in self._peaks.items():
            t_peak = det.poll(t)
            if t_peak is not None:
                self._beacon_update(bid, t, t_peak)

    def _beacon_update(self, bid: str, t_det: float, t_peak: float) -> None:
        """The car was at s_b at t_peak, so it is at s_b + v * (t_det - t_peak) now (A33)."""
        age = t_det - t_peak
        z = np.array([self._beacon_s[bid] + float(self.x[1]) * age])
        # peak-time error (beacon_sigma) plus the speed error accumulated over the age; no effect on the GNSS gate streak
        var = self.beacon_sigma**2 + (age * float(np.sqrt(self.P[1, 1]))) ** 2
        if self._kalman(_H_S, z, np.array([[var]]), gate=BEACON_GATE_CHI2):
            self.beacon_updates += 1

    def estimate(self, t: float) -> Estimate:
        mode: Mode = "dead_reckoning"
        if self._t_acc is not None and t - self._t_acc <= self.gnss_timeout_s:
            mode = self._fix_mode
        return Estimate(t=t, s=float(self.x[0]), v=float(self.x[1]), sigma_s=float(np.sqrt(self.P[0, 0])),
                        sigma_v=float(np.sqrt(self.P[1, 1])), mode=mode,
                        extras={"display_s": self._display_s})


@register
class EkfZuptEstimator(EkfEstimator):
    """The EKF plus zero-velocity and bias updates while the detector says the vehicle is stationary (T8.3, A32)."""

    id = "ekf_zupt"
    label = "EKF + ZUPT"
    zupt = True
    default_params: ClassVar[dict[str, float]] = {
        **EkfEstimator.default_params,
        "zupt_acc_std": 0.05, "zupt_gyro_std": 0.004, "zupt_v_sigma": 0.02, "zupt_gate_chi2": 10.8,
    }
    param_info: ClassVar[dict[str, dict[str, str]]] = {  # A32
        **EkfEstimator.param_info,
        "zupt_acc_std": {"label": "Standstill: accelerometer limit", "unit": "m/s²", "description": "The vehicle counts as stationary when the std of the accelerometer magnitude over 1 s stays below this (and the gyro below its limit) for 0.5 s. Raising it detects standstill more easily, also while driving (A32)."},
        "zupt_gyro_std": {"label": "Standstill: gyro limit", "unit": "rad/s", "description": "The same test for the gyro magnitude: it must stay below this for the vehicle to count as stationary (A32)."},
        "zupt_v_sigma": {"label": "Zero-speed noise", "unit": "m/s", "description": "Standard deviation of the 'speed is 0' measurement applied at 10 Hz while stationary. Smaller means a stronger update (A32)."},
        "zupt_gate_chi2": {"label": "Zero-speed gate", "unit": "chi-square", "description": "Chi-square limit (1 degree of freedom): 'speed is 0' is not applied if the filter's speed and uncertainty cannot be explained by standing still (A32)."},
    }
    constraints: ClassVar[dict[str, dict[str, object]]] = {
        **EkfEstimator.constraints,
        **{k: {"type": "float", "gt": 0} for k in ("zupt_acc_std", "zupt_gyro_std", "zupt_v_sigma", "zupt_gate_chi2")},
    }
