"""Baseline estimator (T5.1): map-matched GNSS, then the last reliable speed during an outage."""
from __future__ import annotations

from collections import deque
from typing import ClassVar

from sim.contracts.estimation import Estimate, Measurement, Mode
from sim.estimators.registry import register
from sim.world.road import RoadMap

# h_acc is the radial 68% value; for a 2-D Gaussian R68 = 1.5096 * sigma_axis
R68_TO_AXIS = 1.5096


@register
class BaselineEstimator:
    id = "baseline"
    label = "Baseline (last speed)"
    default_params: ClassVar[dict[str, float]] = {  # sigma_rate_mps is a tuning value, judged by T5.2
        "gap_timeout_s": 1.5, "n_speed_fixes": 3, "sigma_rate_mps": 0.5, "recover_fixes": 3, "initial_sigma_s": 50.0,
    }
    param_info: ClassVar[dict[str, dict[str, str]]] = {  # display metadata for the UI (T7.9-CR1)
        "gap_timeout_s": {"label": "GNSS gap limit", "unit": "s", "description": "Time without a fix after which the baseline stops using the fix and continues at the held speed. Raising it trusts an old fix for longer."},
        "n_speed_fixes": {"label": "Fixes in the speed average", "unit": "count", "description": "Number of the latest GNSS speeds averaged into the speed that is held through an outage. Raising it smooths noise but follows speed changes more slowly."},
        "sigma_rate_mps": {"label": "Uncertainty growth", "unit": "m/s", "description": "How fast the reported position uncertainty grows per second of outage. It changes the reported sigma only, not the position. A tuning value."},
        "recover_fixes": {"label": "Fixes marked recovering", "unit": "count", "description": "Number of fixes after an outage that carry the mode 'recovering' before 'gnss'. A label only; the position is the same."},
        "initial_sigma_s": {"label": "Initial position uncertainty", "unit": "m", "description": "Position uncertainty reported before the first fix."},
    }
    constraints: ClassVar[dict[str, dict[str, object]]] = {
        "gap_timeout_s": {"type": "float", "gt": 0},
        "n_speed_fixes": {"type": "int", "min": 1},
        "sigma_rate_mps": {"type": "float", "min": 0},
        "recover_fixes": {"type": "int", "min": 1},
        "initial_sigma_s": {"type": "float", "gt": 0},
    }

    def reset(self, road: RoadMap, params: dict) -> None:
        self.road = road
        p = {**self.default_params, **params}
        self.gap_timeout_s = float(p["gap_timeout_s"])
        self.n_speed_fixes = int(p["n_speed_fixes"])
        self.sigma_rate_mps = float(p["sigma_rate_mps"])
        self.recover_fixes = int(p["recover_fixes"])
        self.initial_sigma_s = float(p["initial_sigma_s"])
        self._speeds: deque[float] = deque(maxlen=self.n_speed_fixes)
        self._t_fix: float | None = None
        self._s_fix = 0.0
        self._v_fix = 0.0
        self._sigma_fix = self.initial_sigma_s
        self._sigma_v = 0.0
        self._fix_mode: Mode = "gnss"
        self._recover_left = 0

    def update(self, m: Measurement) -> None:
        if m.kind != "gnss":
            return
        d = m.data
        if self._t_fix is not None and m.t - self._t_fix > self.gap_timeout_s:
            self._recover_left = self.recover_fixes  # first fix after an outage
        self._fix_mode = "recovering" if self._recover_left > 0 else "gnss"
        self._recover_left = max(self._recover_left - 1, 0)
        self._t_fix = m.t
        self._s_fix = float(self.road.project(d["x"], d["y"]))
        self._v_fix = float(d["speed"])
        self._speeds.append(self._v_fix)
        self._sigma_fix = float(d["h_acc"]) / R68_TO_AXIS
        self._sigma_v = float(d["speed_acc"])

    def estimate(self, t: float) -> Estimate:
        if self._t_fix is None:
            return Estimate(t=t, s=0.0, v=0.0, sigma_s=self.initial_sigma_s, sigma_v=0.0, mode="dead_reckoning")
        dt = t - self._t_fix
        if dt > self.gap_timeout_s:
            v = sum(self._speeds) / len(self._speeds)
            sigma = self._sigma_fix + self.sigma_rate_mps * dt
            mode: Mode = "dead_reckoning"
        else:
            v, sigma, mode = self._v_fix, self._sigma_fix, self._fix_mode
        s = min(max(self._s_fix + v * dt, 0.0), self.road.length_m)
        return Estimate(t=t, s=s, v=v, sigma_s=sigma, sigma_v=self._sigma_v, mode=mode)
