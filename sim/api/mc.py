"""Small in-memory Monte Carlo for the live demo (POST /api/montecarlo); reuses sim.eval.montecarlo, writes no CSV."""
from __future__ import annotations

import multiprocessing
import os
import threading
import time
from concurrent.futures import ProcessPoolExecutor, wait
from typing import Any

import numpy as np

from sim.contracts.scenario import Scenario
from sim.eval import montecarlo as mc

MAX_SECONDS = 60.0  # a request projected to take longer is rejected
WORKERS = os.cpu_count() or 1
_pool: ProcessPoolExecutor | None = None
_busy = threading.Lock()  # one Monte Carlo at a time: a second one would just share the same cores


class TooSlow(Exception):
    pass


class Busy(Exception):
    pass


def _get_pool() -> ProcessPoolExecutor:
    global _pool
    if _pool is None:  # spawn, not fork: the server has threads, and spawn behaves the same on every OS
        _pool = ProcessPoolExecutor(WORKERS, mp_context=multiprocessing.get_context("spawn"))
    return _pool


def _percentile(v: list[float], q: float) -> float | None:
    return float(np.percentile(np.abs(v), q)) if v else None


def summarize(sc: Scenario, params: dict[str, dict], rows: list[dict[str, Any]]) -> dict[str, dict]:
    """Per estimator, for the first vehicle: signed exit errors per tunnel (one per seed), consistency per run and the statistics."""
    vehicle = sc.vehicles[0].id
    tunnels = [t.id for t in sc.road.tunnels][:mc.MAX_TUNNELS]
    out = {}
    for est in params:
        g = [r for r in rows if r["vehicle"] == vehicle and r["estimator"] == est]  # already in seed order
        errors = {tid: [r[f"exit_error_m_t{i}"] for r in g if r[f"exit_error_m_t{i}"] != ""] for i, tid in enumerate(tunnels)}
        cons = [r["consistency_pct"] for r in g if r["consistency_pct"] != ""]
        out[est] = {
            "exit_error_m": errors,
            "consistency_pct": cons,
            "median_abs_exit_error_m": {t: _percentile(v, 50) for t, v in errors.items()},
            "p90_abs_exit_error_m": {t: _percentile(v, 90) for t, v in errors.items()},
            "mean_consistency_pct": float(np.mean(cons)) if cons else None,
        }
    return out


def run(sc: Scenario, params: dict[str, dict], n_seeds: int) -> dict[str, Any]:
    """Blocking: call it from a worker thread. Raises TooSlow when the first tasks show it would exceed MAX_SECONDS."""
    if not _busy.acquire(blocking=False):
        raise Busy
    try:
        t0 = time.perf_counter()
        pool = _get_pool()
        futures = [pool.submit(mc.timed_task, t) for t in mc.inline_tasks(sc, params, n_seeds)]
        first = futures[:WORKERS]  # the first wave starts together, so its task times say how long the rest takes
        done, _ = wait(first, timeout=MAX_SECONDS)
        projected = None
        if len(done) == len(first):
            projected = float(np.mean([f.result()[1] for f in first])) * n_seeds / WORKERS
        if projected is None or projected > MAX_SECONDS:
            for f in futures:
                f.cancel()  # tasks already running finish on their own
            raise TooSlow(f"this run would take {'over ' + str(int(MAX_SECONDS)) if projected is None else '~' + str(int(projected))} s "
                          f"on {WORKERS} cores (limit {int(MAX_SECONDS)} s): use fewer seeds or fewer estimators")
        rows = [r for f in futures for r in f.result()[0]]
        return {"scenario": sc.id, "n_seeds": n_seeds, "tunnels": [t.id for t in sc.road.tunnels][:mc.MAX_TUNNELS],
                "seconds": round(time.perf_counter() - t0, 1), "estimators": summarize(sc, params, rows)}
    finally:
        _busy.release()
