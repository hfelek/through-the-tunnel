"""Trace metrics (CONTRACTS 3.5). Uses truth, so nothing under sim/estimators may import this module."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

RECOVERY_BAND_M = 10.0
CONSISTENCY_K = 2.0


def _cross_t(truth_t: np.ndarray, truth_s: np.ndarray, s: float) -> float | None:
    """Time at which the true s first reaches `s`; None if it never does."""
    if truth_s[0] > s or truth_s[-1] < s:
        return None
    i = max(int(np.searchsorted(truth_s, s, side="left")), 1)
    s0, s1 = truth_s[i - 1], truth_s[i]
    return float(truth_t[i - 1] + (truth_t[i] - truth_t[i - 1]) * (s - s0) / (s1 - s0)) if s1 > s0 else float(truth_t[i])


def _recovery_s(t: np.ndarray, err: np.ndarray, t_start: float, t_end: float) -> float | None:
    """Time from t_start until |err| < band and stays so through t_end; None if never."""
    win = (t >= t_start) & (t <= t_end)
    if not win.any():
        return None
    bad = np.flatnonzero(np.abs(err[win]) >= RECOVERY_BAND_M)
    if len(bad) == 0:
        return float(t[win][0] - t_start)
    k = bad[-1] + 1
    return float(t[win][k] - t_start) if k < win.sum() else None


def compute_metrics(
    est_t: Sequence[float], est_s: Sequence[float], est_sigma_s: Sequence[float], est_display_s: Sequence[float],
    truth_t: Sequence[float], truth_s: Sequence[float],
    tunnels: Sequence[tuple[str, float, float]], fix_t: Sequence[float],
    callouts: Sequence[Any] = (),
) -> dict[str, Any]:
    """Metrics for one estimator on one vehicle; `tunnels` are (id, start_s, end_s). Empty dict without truth."""
    if len(truth_t) < 2 or len(est_t) == 0:
        return {}
    et, es, sig, disp = (np.asarray(a, dtype=float) for a in (est_t, est_s, est_sigma_s, est_display_s))
    tt, ts, fx = np.asarray(truth_t, dtype=float), np.asarray(truth_s, dtype=float), np.asarray(fix_t, dtype=float)
    s_true = np.interp(et, tt, ts)
    err = es - s_true
    inside = np.zeros(len(et), dtype=bool)
    for _, a, b in tunnels:
        inside |= (s_true >= a) & (s_true <= b)
    ein = err[inside]
    out: dict[str, Any] = {
        "error": err.tolist(),
        "rmse_in_tunnel_m": float(np.sqrt(np.mean(ein**2))) if len(ein) else None,
        "max_abs_error_in_tunnel_m": float(np.max(np.abs(ein))) if len(ein) else None,
        "consistency_pct": float(100 * np.mean(np.abs(ein) < CONSISTENCY_K * sig[inside])) if len(ein) else None,
        "max_display_jump_m": float(np.max(np.abs(np.diff(disp) - np.diff(s_true)))) if len(et) > 1 else 0.0,
        "exit_error_m": {}, "recovery_time_s": {},
        "callout_timing_error_s": {},
    }
    for c in callouts:
        out["callout_timing_error_s"].setdefault(c.exit, {})[str(int(c.distance_m))] = float(c.t - c.t_ideal)
    for i, (tid, _, end_s) in enumerate(tunnels):
        t_exit = _cross_t(tt, ts, end_s)
        out["exit_error_m"][tid] = None if t_exit is None else float(np.interp(t_exit, et, err))
        fixes = fx[fx >= t_exit] if t_exit is not None else fx[:0]
        if len(fixes) == 0:
            out["recovery_time_s"][tid] = None
            continue
        t_next = _cross_t(tt, ts, tunnels[i + 1][1]) if i + 1 < len(tunnels) else None
        out["recovery_time_s"][tid] = _recovery_s(et, err, float(fixes[0]), t_next if t_next is not None else float(et[-1]))
    return out
