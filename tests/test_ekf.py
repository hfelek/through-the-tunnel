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


def test_display_is_monotonic_and_the_filter_recovers():
    for name in ("short_straight_500m", "hard_brake_inside", "stop_and_go_3km"):
        v = run_scenario(load_scenario(f"scenarios/{name}.json"), {"baseline": {}, "ekf_zupt": {}}).vehicles[0]
        e, base = v.estimates["ekf_zupt"], v.metrics["baseline"]
        assert all(b >= a for a, b in zip(e.display_s, e.display_s[1:])), name
        m = v.metrics["ekf_zupt"]
        assert m["max_display_jump_m"] < base["max_display_jump_m"], name
        assert all(r is not None for r in m["recovery_time_s"].values()), name  # the gate safeguard (T8.6)


def test_beacons_bound_the_error_and_change_nothing_without_beacons():
    on = run_scenario(load_scenario("scenarios/beacons_5km.json"), {"ekf_zupt": {}}).vehicles[0]
    assert on.metrics["ekf_zupt"]["rmse_in_tunnel_m"] < 20.0  # A33: a beacon every 400 m bounds the drift
    sc = load_scenario("scenarios/curved_2km.json")
    assert not sc.beacons.enabled  # no beacons: the map has none, so the beacon code never runs (T8.5)
    est = run_scenario(sc, {"ekf_zupt": {}}).vehicles[0].estimates["ekf_zupt"]
    assert run_scenario(sc, {"ekf_zupt": {"beacon_sigma": 1.0}}).vehicles[0].estimates["ekf_zupt"].s == est.s
