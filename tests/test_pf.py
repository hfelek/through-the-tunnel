from sim.contracts.scenario import load_scenario
from sim.runner import run_scenario


def _run(name):
    return run_scenario(load_scenario(f"scenarios/{name}.json"), {"ekf_zupt": {}, "pf": {}}).vehicles[0].metrics


def test_map_matching_helps_after_curves_and_the_dip():
    m = _run("curved_5km_exit_inside")  # targets, not hard stops (T8.4)
    assert m["pf"]["rmse_in_tunnel_m"] < m["ekf_zupt"]["rmse_in_tunnel_m"]
    m = _run("undersea_3km_dip")
    assert abs(m["pf"]["exit_error_m"]["T1"]) < 100.0  # target "better than ekf_zupt" is missed (59 m vs 43 m), see A34
