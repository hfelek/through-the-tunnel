"""Particle filter with map matching (T8.4, docs/design/T8.4_pf.md, A34): an EKF+ZUPT plus curvature matching (CR2: no barometer)."""
from __future__ import annotations

from typing import ClassVar

import numpy as np

from sim.contracts.estimation import Estimate, Measurement
from sim.estimators.ekf import EkfZuptEstimator
from sim.estimators.registry import register
from sim.world.road import RoadMap

STEP_S = 0.1  # particles move at 10 Hz
WEIGH_S = 1.0  # weights use 1 s averages

_OWN: dict[str, float] = {  # A34
    "n": 500, "dv_rw": 0.05, "sigma_yaw": 0.005, "jitter_s": 1.0, "jitter_v": 0.05, "seed": 0,
    "informative_ratio": 0.5,  # CR3
}


def systematic_resample(w: np.ndarray, u: float) -> np.ndarray:
    """Indices drawn at the evenly spaced points (u + k) / n of the cumulative weights; one random number only."""
    n = len(w)
    idx = np.searchsorted(np.cumsum(w), (u + np.arange(n)) / n)
    return np.minimum(idx, n - 1)  # rounding can push the last point just past 1.0


@register
class PfEstimator:
    id = "pf"
    label = "Particle filter (map matching)"
    default_params: ClassVar[dict[str, float]] = {**_OWN, **EkfZuptEstimator.default_params}
    constraints: ClassVar[dict[str, dict[str, object]]] = {
        **EkfZuptEstimator.constraints,
        **{k: {"type": "float", "gt": 0} for k in _OWN if k not in ("n", "seed")},
        "n": {"type": "int", "min": 10},
        "seed": {"type": "int", "min": 0},
    }

    def reset(self, road: RoadMap, params: dict) -> None:
        p = {**self.default_params, **params}
        for k in _OWN:
            setattr(self, k, p[k])
        self.n = int(self.n)
        self.road = road
        self.ekf = EkfZuptEstimator()
        self.ekf.reset(road, {k: v for k, v in params.items() if k not in _OWN})
        self.rng = np.random.default_rng(int(self.seed))  # all randomness comes from here
        self.s, self.dv, self.w = np.zeros(self.n), np.zeros(self.n), np.full(self.n, 1.0 / self.n)
        self._seen = (None, 0)  # (last accepted fix time, beacon updates) of the EKF: a change means a new absolute fix
        self._started = False
        self._t_prop: float | None = None  # last particle step
        self._t_weigh: float | None = None  # last weighing; None until the tunnel stretch has taken its first step
        self._pvv_prev = float(self.ekf.P[1, 1])  # EKF speed variance at the previous particle step
        self._clear_averages()
        self._display_s = 0.0

    # -- helpers ----------------------------------------------------------------------------------------------------
    def _clear_averages(self) -> None:
        self._yaw_sum, self._yaw_n = 0.0, 0
        self._exp_sum, self._exp_n = np.zeros(self.n), 0

    def _in_tunnel(self, t: float) -> bool:
        """No current GNSS fix after the first one: map matching is on (design note)."""
        return self.ekf._have_fix and self.ekf.estimate(t).mode == "dead_reckoning"

    def _mean_std(self) -> tuple[float, float]:
        mean = float(self.w @ self.s)
        return mean, float(np.sqrt(self.w @ (self.s - mean) ** 2))

    def _redraw(self) -> None:
        """A new absolute fix (GNSS or beacon): particles are a fresh sample of the EKF's belief."""
        x, p = self.ekf.x, self.ekf.P
        self.s = np.clip(self.rng.normal(x[0], np.sqrt(p[0, 0]), self.n), 0.0, self.road.length_m)
        self.dv = self.rng.normal(0.0, np.sqrt(p[1, 1]), self.n)
        self.w = np.full(self.n, 1.0 / self.n)
        self._pvv_prev = float(p[1, 1])
        self._t_weigh = None  # the weighing clock restarts with the next tunnel step
        self._clear_averages()
        if not self._started:
            self._started, self._display_s = True, float(x[0])

    # -- Estimator interface ----------------------------------------------------------------------------------------
    def update(self, m: Measurement) -> None:
        self.ekf.update(m)  # the EKF sees everything and keeps its own GNSS, ZUPT and beacon logic
        if m.kind == "imu":
            self._imu(m)
        elif (self.ekf._t_acc, self.ekf.beacon_updates) != self._seen:
            self._seen = (self.ekf._t_acc, self.ekf.beacon_updates)
            self._redraw()

    def _imu(self, m: Measurement) -> None:
        a = self.ekf.aligned
        if a is not None and a.valid:  # the gyro is only meaningful once the phone is aligned
            self._yaw_sum += a.yaw_rate
            self._yaw_n += 1
        if self._t_prop is None:
            self._t_prop = m.t
        elif m.t - self._t_prop >= STEP_S:
            dt, self._t_prop = m.t - self._t_prop, m.t
            self._step(m.t, dt)

    def _step(self, t: float, dt: float) -> None:
        if not self._started:
            return
        v = float(self.ekf.x[1])
        self._propagate(dt, v)  # always, also with a current fix: the cloud must not stand still between redraws (CR6)
        if self._in_tunnel(t):
            if self._t_weigh is None:  # first tunnel step: the 1 s averages start here, not at the last GNSS fix
                self._t_weigh = t
                self._clear_averages()
            if t - self._t_weigh >= WEIGH_S:
                self._weigh(t)
            target = self._mean_std()[0]
        else:
            self._t_weigh = None  # GNSS current: the next tunnel stretch starts its own clock
            target = float(self.ekf.x[0])  # GNSS current: the particles are the EKF's belief
        self._advance_display(target, v, dt)

    def _propagate(self, dt: float, v: float) -> None:
        self.dv += self.rng.normal(0.0, self.dv_rw * np.sqrt(dt), self.n)  # random walk of the speed offsets
        pvv = float(self.ekf.P[1, 1])
        grow = max(0.0, pvv - self._pvv_prev)  # CR1: the particles must grow their speed spread like the EKF's P_vv
        self._pvv_prev = pvv
        self.dv += self.rng.normal(0.0, np.sqrt(grow), self.n)
        v_i = v + self.dv
        self.s = np.clip(self.s + v_i * dt, 0.0, self.road.length_m)
        self._exp_sum += v_i * self.road.at(self.s)["curvature"]  # expected yaw rate of each particle
        self._exp_n += 1

    def _weigh(self, t: float) -> None:
        """Curvature likelihood and resampling, but only when the map can tell the particles apart (CR3)."""
        expected = self._exp_sum / max(self._exp_n, 1)  # each particle's mean yaw rate over the second
        mean_exp = float(self.w @ expected)
        spread = float(np.sqrt(self.w @ (expected - mean_exp) ** 2))
        if spread >= self.informative_ratio * self.sigma_yaw:  # else e.g. a straight road: all particles predict the same yaw rate, keep them
            self._weigh_and_resample(expected)
        self._t_weigh = t
        self._clear_averages()

    def _weigh_and_resample(self, expected: np.ndarray) -> None:
        if self._yaw_n > 0:  # measured yaw rate against v * curvature at the particle's position
            err = self._yaw_sum / self._yaw_n - expected
            self.w = self.w * np.exp(-0.5 * (err / self.sigma_yaw) ** 2)
        total = self.w.sum()
        self.w = self.w / total if total > 1e-300 else np.full(self.n, 1.0 / self.n)  # all weights vanished: start over
        if 1.0 / float(self.w @ self.w) < self.n / 2:  # N_eff
            idx = systematic_resample(self.w, float(self.rng.random()))
            self.s, self.dv = self.s[idx], self.dv[idx]
            self.w = np.full(self.n, 1.0 / self.n)
            self.s = np.clip(self.s + self.rng.normal(0.0, self.jitter_s, self.n), 0.0, self.road.length_m)
            self.dv = self.dv + self.rng.normal(0.0, self.jitter_v, self.n)  # jitter: no collapse onto copies

    def _advance_display(self, target: float, v: float, dt: float) -> None:
        """The T8.6 rule on the particle position: never backwards, catches up at most display_max_catchup faster."""
        e = self.ekf
        rate = v + e.display_k * (target - self._display_s)
        self._display_s += min(max(rate, 0.0), v + e.display_max_catchup) * dt
        self._display_s = min(self._display_s, self.road.length_m)

    def estimate(self, t: float) -> Estimate:
        e = self.ekf.estimate(t)
        if self._started and self._in_tunnel(t):
            mean, std = self._mean_std()
            e = Estimate(t=t, s=mean, v=e.v + float(self.w @ self.dv), sigma_s=std, sigma_v=e.sigma_v, mode=e.mode)
        e.extras = {"display_s": self._display_s}
        return e
