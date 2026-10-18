"""Callout logic (T5.3). `compute_callouts` sees only the estimate; `ideal_times` uses truth (metrics side)."""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from sim.contracts.trace import Callout
from sim.eval.metrics import _cross_t

DISTANCES_M = (500, 200, 0)


def fire_times(
    est_t: Sequence[float], est_s: Sequence[float], est_sigma_s: Sequence[float],
    exits: Sequence[tuple[str, float]], k: float,
) -> dict[tuple[str, int], float]:
    """First output sample with s + k*sigma >= exit_s - d; skipped if already true at the first sample."""
    t, reach = np.asarray(est_t, dtype=float), np.asarray(est_s, dtype=float) + k * np.asarray(est_sigma_s, dtype=float)
    out: dict[tuple[str, int], float] = {}
    for eid, exit_s in exits:
        for d in DISTANCES_M:
            hit = np.flatnonzero(reach >= exit_s - d)
            if len(hit) and hit[0] > 0:
                out[(eid, d)] = float(t[hit[0]])
    return out


def ideal_times(
    truth_t: Sequence[float], truth_s: Sequence[float], exits: Sequence[tuple[str, float]],
) -> dict[tuple[str, int], float]:
    """Time the true s crosses exit_s - d; skipped if the vehicle starts past that point."""
    tt, ts = np.asarray(truth_t, dtype=float), np.asarray(truth_s, dtype=float)
    out: dict[tuple[str, int], float] = {}
    for eid, exit_s in exits:
        for d in DISTANCES_M:
            t = _cross_t(tt, ts, exit_s - d)
            if t is not None:
                out[(eid, d)] = t
    return out


def compute_callouts(
    est_t: Sequence[float], est_s: Sequence[float], est_sigma_s: Sequence[float],
    truth_t: Sequence[float], truth_s: Sequence[float], exits: Sequence[tuple[str, float]], k: float = 1.0,
) -> list[Callout]:
    """Callouts that both fired and have an ideal time; the estimate and truth paths are separate."""
    fired = fire_times(est_t, est_s, est_sigma_s, exits, k)
    ideal = ideal_times(truth_t, truth_s, exits)
    return [
        Callout(exit=e, distance_m=d, t=t, t_ideal=ideal[(e, d)])
        for (e, d), t in fired.items() if (e, d) in ideal
    ]
