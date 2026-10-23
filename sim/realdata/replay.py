"""Run the estimators on a converted real recording with the GNSS removed in a window (T10.5a).

The window is declared tunnel T1; the removed fixes, projected on the map, are the (partial) truth the metrics use.
Times in and out of `replay` are trace time (seconds since the start of the span); the API converts recording time.
"""
from __future__ import annotations

import numpy as np

from sim.contracts.scenario import Tunnel
from sim.contracts.trace import Event, Gnss, Measurements, Trace, VehicleTrace
from sim.eval.metrics import compute_metrics
from sim.realdata.sensor_logger import map_of
from sim.runner import _map_columns, _run_estimators

# A real city drive is hillier and more curved than the simulator's roads, so the aligner's calibration conditions are
# relaxed (found in the T10 check). Applied only to estimators that have the two parameters.
REAL_CALIBRATION = {"flat_grade": 0.03, "straight_curvature": 2e-3}
AFTER_EXIT_S = 60.0  # keep running this long after the outage, to see the recovery
OUTPUT_HZ = 10.0


def replay(trace: Trace, ta: float, tb: float, estimators: dict[str, dict]) -> Trace:
    rm, veh = map_of(trace), trace.vehicles[0]
    truth, imu, g = veh.truth, veh.measurements.imu, veh.measurements.gnss
    # the outage edges in s: where the (projected) GNSS track is at ta and tb
    rm.tunnels = [Tunnel(id="T1", start_s=float(np.interp(ta, truth.t, truth.s)), end_s=float(np.interp(tb, truth.t, truth.s)))]
    gt = np.asarray(g.t)
    keep = (gt < ta) | (gt > tb)
    gnss = {c: np.asarray(a)[keep] for c, a in g.model_dump().items()}
    sensors = {"imu": {c: np.asarray(a) for c, a in imu.model_dump().items()}, "gnss": gnss}
    t_end = float(min(tb + AFTER_EXIT_S, imu.t[-1]))
    est, compute_us = _run_estimators(rm, sensors, 0.0, t_end, OUTPUT_HZ, estimators)
    tunnels = [(t.id, t.start_s, t.end_s) for t in rm.tunnels]
    metrics = {k: compute_metrics(e.t, e.s, e.sigma_s, e.display_s, truth.t, truth.s, tunnels, gnss["t"].tolist()) for k, e in est.items()}
    for k in est:
        metrics[k]["compute_us_per_measurement"] = compute_us[k]
        # undefined here: the GNSS returns clean after an artificial outage, so "recovery" is always about 0 s and does
        # not separate the methods (in a simulation the first fixes after a tunnel are bad on purpose)
        metrics[k]["recovery_time_s"] = {}
    events = [Event(t=ta, type="tunnel_enter", ref="T1"), Event(t=tb, type="tunnel_exit", ref="T1")]
    veh_out = VehicleTrace(
        id=veh.id, truth=truth, measurements=Measurements(imu=imu, gnss=Gnss(**{c: a.tolist() for c, a in gnss.items()})),
        events=events, estimates=est, metrics=metrics,
    )
    return Trace(source="real", scenario_id=trace.scenario_id, map=_map_columns(rm), vehicles=[veh_out])
