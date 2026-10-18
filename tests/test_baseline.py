from pathlib import Path

import numpy as np

from sim.contracts.scenario import load_scenario
from sim.runner import run_scenario

SCEN = Path(__file__).resolve().parents[1] / "scenarios"


def exit_error(name: str, jitter: bool = True) -> float:
    """Along-track error (m) at the moment the true vehicle leaves the first tunnel."""
    sc = load_scenario(SCEN / f"{name}.json")
    if not jitter:
        sc = sc.model_copy(deep=True)
        for veh in sc.vehicles:
            veh.speed_jitter_kmh = 0.0
    tr = run_scenario(sc, estimators={"baseline": {}})
    end_s = tr.map.tunnels[0]["end_s"]
    v = tr.vehicles[0]
    t_exit = float(np.interp(end_s, v.truth.s, v.truth.t))
    est = v.estimates["baseline"]
    return float(np.interp(t_exit, est.t, est.s) - end_s)


def test_constant_speed_exit_error_small():
    """Constant speed means no driver speed jitter (A27); jitter alone moves the error by ~20 m."""
    assert abs(exit_error("curved_2km", jitter=False)) < 20.0


def test_stop_and_go_exit_error_large():
    """Expected failure the plan asks for: the baseline keeps its entry speed through the stops."""
    assert abs(exit_error("stop_and_go_3km")) > 100.0
