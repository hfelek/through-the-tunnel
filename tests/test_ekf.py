from sim.contracts.scenario import load_scenario
from sim.runner import run_scenario


def _metrics(name):
    sc = load_scenario(f"scenarios/{name}.json")
    m = run_scenario(sc, {"baseline": {}, "ekf": {}}).vehicles[0].metrics
    assert m["ekf"]["compute_us_per_measurement"] > 0
    return m["baseline"], m["ekf"]


def test_ekf_is_consistent_on_curved_2km():
    _, ekf = _metrics("curved_2km")
    assert ekf["consistency_pct"] >= 85
