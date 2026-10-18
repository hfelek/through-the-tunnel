import numpy as np

from sim.eval.callouts import compute_callouts

EXITS = [("E1", 1000.0)]
T = np.arange(0, 100.05, 0.1)  # 10 m/s, 10 Hz output
S = 10.0 * T


def test_perfect_estimate_fires_at_ideal_time():
    cs = compute_callouts(T, S, np.zeros_like(T), T, S, EXITS, k=1.0)
    assert sorted(c.distance_m for c in cs) == [0, 200, 500]
    assert all(abs(c.t - c.t_ideal) <= 0.1 + 1e-9 for c in cs)


def test_larger_k_fires_earlier_or_equal():
    sig = np.full_like(T, 30.0)
    t_by_k = [{c.distance_m: c.t for c in compute_callouts(T, S, sig, T, S, EXITS, k=k)} for k in (0.0, 1.0, 2.0)]
    for d in (500, 200, 0):
        assert t_by_k[0][d] >= t_by_k[1][d] >= t_by_k[2][d]
    assert t_by_k[2][200] < t_by_k[0][200]
