import pytest

from sim.eval.metrics import compute_metrics

# truth: 10 m/s for 10 s; tunnel T1 covers s 20..60 (t = 2..6)
TT = [0.0, 10.0]
TS = [0.0, 100.0]
TUN = [("T1", 20.0, 60.0)]


def test_error_rmse_and_exit_error():
    t = [0, 1, 2, 3, 4, 5, 6, 7]
    s = [0, 10, 23, 34, 46, 58, 66, 74]  # errors 0,0,3,4,6,8,6,4 -> truth at t is 10*t
    m = compute_metrics(t, s, [1] * 8, s, TT, TS, TUN, fix_t=[0, 1, 7])
    assert m["error"] == pytest.approx([0, 0, 3, 4, 6, 8, 6, 4])
    assert m["rmse_in_tunnel_m"] == pytest.approx(((9 + 16 + 36 + 64 + 36) / 5) ** 0.5)  # t = 2..6
    assert m["max_abs_error_in_tunnel_m"] == pytest.approx(8.0)
    assert m["exit_error_m"]["T1"] == pytest.approx(6.0)  # error at t = 6
    assert m["max_display_jump_m"] == pytest.approx(3.0)  # step 1->2: estimate advances 13 m vs 10 m true


def test_consistency_and_recovery_time():
    t = list(range(10))
    err = [0, 0, 1, 1, 3, 3, 20, 12, 8, 2]  # after exit at t = 6, error drops below 10 at t = 8
    s = [10 * k + e for k, e in zip(t, err)]
    sig = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    m = compute_metrics(t, s, sig, s, TT, TS, TUN, fix_t=[0, 1, 2, 7.5])
    # in tunnel t = 2..6: |err| = 1,1,3,3,20 vs 2 sigma = 2 -> only the two 1 m samples are consistent
    assert m["consistency_pct"] == pytest.approx(40.0)
    assert m["recovery_time_s"]["T1"] == pytest.approx(0.5)  # first fix 7.5, |err| < 10 from t = 8
