from sim.contracts.scenario import load_scenario
from sim.runner import run_scenario


def _run(name):
    return run_scenario(load_scenario(f"scenarios/{name}.json"), {"ekf_zupt": {}, "pf": {}}).vehicles[0].metrics


def test_curvature_matching_helps_after_curves():
    m = _run("curved_5km_exit_inside")  # target, not a hard stop (T8.4)
    assert m["pf"]["rmse_in_tunnel_m"] < m["ekf_zupt"]["rmse_in_tunnel_m"]
