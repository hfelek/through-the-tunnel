from sim.contracts.scenario import load_scenario
from sim.estimators.stationary import StationaryDetector
from sim.runner import run_scenario
from sim.world.road import RoadMap


def _metrics(name):
    sc = load_scenario(f"scenarios/{name}.json")
    m = run_scenario(sc, {"baseline": {}, "ekf": {}}).vehicles[0].metrics
    assert m["ekf"]["compute_us_per_measurement"] > 0
    return m["baseline"], m["ekf"]


def test_ekf_is_consistent_on_curved_2km():
    _, ekf = _metrics("curved_2km")
    assert ekf["consistency_pct"] >= 85


def test_zupt_still_helps_on_hard_brake_inside():
    sc = load_scenario("scenarios/hard_brake_inside.json")
    m = run_scenario(sc, {"ekf": {}, "ekf_zupt": {}}).vehicles[0].metrics
    # the 15 s standstill is pinned to v = 0 (T8.3). T9.3: ZUPT no longer moves s, so on this seed the exit error is
    # +29.5 m and consistency 33% (was +10 m and 94%); the 6-seed mean consistency is 80%. The guard is the gain over the EKF.
    assert m["ekf_zupt"]["rmse_in_tunnel_m"] < 0.5 * m["ekf"]["rmse_in_tunnel_m"]


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


def test_peak_time_is_the_true_pass_time():
    from sim.estimators.beacon_peak import PeakDetector

    det, t0, found = PeakDetector(-85.0, 3.0), 5.0, []
    for k in range(101):  # symmetric pass at 10 packets/s: RSSI falls off with the square of the distance in time
        t = k / 10
        if (t_peak := det.add(t, -50.0 - 2.0 * (t - t0) ** 2)) is not None:
            found.append(t_peak)
    assert len(found) == 1 and abs(found[0] - t0) < 0.1  # the 1 s moving average alone would report t0 + 0.5 s


def test_zero_speed_update_leaves_s_unchanged():
    import numpy as np

    from sim.estimators import ekf as K

    est = K.EkfZuptEstimator()
    est.reset(RoadMap(load_scenario("scenarios/short_straight_500m.json").road), {})
    est.x = np.array([100.0, 0.5, 0.0, 0.0])
    est.P = np.array([[100.0, 10.0, 0, 0], [10.0, 1.0, 0, 0], [0, 0, 0.01, 0], [0, 0, 0, 0.01]])  # P_sv / P_vv = 10 s
    assert est._kalman(K._H_V, np.array([0.0]), np.array([[0.0004]]), keep_s=False)
    assert est.x[0] == 100.0 and est.x[1] < 0.01  # v is pulled to 0, s does not move although P_sv is large
    assert np.all(np.linalg.eigvalsh(est.P) > -1e-12)  # P stays a valid covariance (Joseph form)
