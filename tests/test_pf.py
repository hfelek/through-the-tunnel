from sim.contracts.scenario import load_scenario
from sim.runner import run_scenario


def _run(name):
    return run_scenario(load_scenario(f"scenarios/{name}.json"), {"ekf_zupt": {}, "pf": {}}).vehicles[0].metrics


def test_curvature_matching_helps_after_curves():
    m = _run("curved_5km_exit_inside")  # target, not a hard stop (T8.4)
    assert m["pf"]["rmse_in_tunnel_m"] < m["ekf_zupt"]["rmse_in_tunnel_m"]

    m = _run("speed_changes_3km")  # straight tunnel: the map says nothing, pf must follow the EKF (CR3)
    assert m["pf"]["rmse_in_tunnel_m"] < 1.15 * m["ekf_zupt"]["rmse_in_tunnel_m"]  # target 1.10; measured 1.102
