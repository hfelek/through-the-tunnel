from sim.contracts.scenario import load_scenario
from sim.estimators.stationary import StationaryDetector
from sim.runner import run_scenario


def _metrics(name):
    sc = load_scenario(f"scenarios/{name}.json")
    m = run_scenario(sc, {"baseline": {}, "ekf": {}}).vehicles[0].metrics
    assert m["ekf"]["compute_us_per_measurement"] > 0
    return m["baseline"], m["ekf"]


def test_ekf_is_consistent_on_curved_2km():
    _, ekf = _metrics("curved_2km")
    assert ekf["consistency_pct"] >= 85


def test_zupt_keeps_hard_brake_inside_consistent():
    sc = load_scenario("scenarios/hard_brake_inside.json")
    m = run_scenario(sc, {"ekf_zupt": {}}).vehicles[0].metrics["ekf_zupt"]
    assert m["consistency_pct"] >= 85  # the 15 s standstill is pinned to v = 0 (T8.3)


def test_no_stationary_detection_at_constant_speed():
    for name in ("curved_2km", "beacons_5km"):
        imu = run_scenario(load_scenario(f"scenarios/{name}.json")).vehicles[0].measurements.imu
        det = StationaryDetector(0.05, 0.004)  # the EKF+ZUPT defaults
        rows = zip(imu.t, imu.ax, imu.ay, imu.az, imu.gx, imu.gy, imu.gz)
        assert not any(det.update(*row) for row in rows), name
