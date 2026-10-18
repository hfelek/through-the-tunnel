from pathlib import Path

import numpy as np

from sim.contracts.scenario import load_scenario
from sim.runner import run_scenario

SCEN = Path(__file__).resolve().parents[1] / "scenarios"


def exit_error(name: str) -> float:
    """Along-track error (m) at the moment the true vehicle leaves the first tunnel."""
    tr = run_scenario(load_scenario(SCEN / f"{name}.json"), estimators={"baseline": {}})
    end_s = tr.map.tunnels[0]["end_s"]
    v = tr.vehicles[0]
    t_exit = float(np.interp(end_s, v.truth.s, v.truth.t))
    est = v.estimates["baseline"]
    return float(np.interp(t_exit, est.t, est.s) - end_s)


def test_constant_speed_exit_error_small():
    assert abs(exit_error("curved_2km")) < 20.0


def test_stop_and_go_exit_error_large():
    """Expected failure the plan asks for: the baseline keeps its entry speed through the stops."""
    assert abs(exit_error("stop_and_go_3km")) > 100.0
