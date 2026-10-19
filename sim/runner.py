"""Scenario runner (docs/CONTRACTS.md 3.3-3.4): sensors -> trace, estimators fed measurements only."""
from __future__ import annotations

import time

import numpy as np

from sim.contracts.estimation import Estimator, Measurement
from sim.contracts.preset import load_preset
from sim.contracts.scenario import Scenario
from sim.contracts.trace import (
    Baro,
    Ble,
    EstimateColumns,
    Event,
    Gnss,
    Imu,
    Mag,
    MapColumns,
    Measurements,
    Trace,
    Truth,
    VehicleTrace,
)
from sim.estimators.registry import EstimatorFailed, get_estimator
from sim.eval.callouts import compute_callouts, ideal_times, missed_callouts
from sim.eval.metrics import compute_metrics
from sim.sensors.baro import generate_baro
from sim.sensors.ble import generate_ble
from sim.sensors.gnss import generate_gnss
from sim.sensors.imu import MountPath, generate_imu
from sim.sensors.mag import generate_mag
from sim.world.road import RoadMap
from sim.world.vehicle import VehicleMotion, simulate_vehicles

# fixed order: used for the per-vehicle rng spawn and for tie-breaking at equal t. Never reorder.
KINDS = ("imu", "gnss", "baro", "mag", "ble")
_MODELS = {"imu": Imu, "gnss": Gnss, "baro": Baro, "mag": Mag, "ble": Ble}


def _map_columns(road_map: RoadMap) -> MapColumns:
    line = road_map.line
    cols = {n: getattr(line, n).tolist() for n in ("s", "x", "y", "z", "heading", "curvature", "grade")}
    return MapColumns(
        **cols,
        tunnels=[t.model_dump() for t in road_map.tunnels],
        exits=[e.model_dump() for e in road_map.exits],
        speed_limits=[s.model_dump() for s in road_map.speed_limits],
    )


def _truth(motion: VehicleMotion, road_map: RoadMap) -> Truth:
    pos = road_map.at(motion.s)
    return Truth(
        t=motion.t.tolist(), s=motion.s.tolist(), v=motion.v.tolist(), a=motion.a.tolist(),
        x=pos["x"].tolist(), y=pos["y"].tolist(), z=pos["z"].tolist(),
        yaw=motion.yaw.tolist(), pitch=motion.pitch.tolist(),
    )


def _events(motion: VehicleMotion, road_map: RoadMap, handling) -> list[Event]:
    events = [Event(t=h.t, type="handling") for h in handling]
    for tun in road_map.tunnels:
        for s_edge, kind in ((tun.start_s, "tunnel_enter"), (tun.end_s, "tunnel_exit")):
            i = int(np.searchsorted(motion.s, s_edge, side="left"))
            if i < len(motion.t) and (i > 0 or motion.s[0] >= s_edge):
                events.append(Event(t=float(motion.t[i]), type=kind, ref=tun.id))
    return sorted(events, key=lambda e: e.t)


def _merged(sensors: dict[str, dict[str, np.ndarray]]) -> list[Measurement]:
    """All samples as Measurement objects, ordered by t, then by KINDS order."""
    t = np.concatenate([sensors[k]["t"] for k in KINDS if k in sensors])
    kind_idx = np.concatenate([np.full(len(sensors[k]["t"]), i) for i, k in enumerate(KINDS) if k in sensors])
    order = np.lexsort((np.arange(len(t)), kind_idx, t))
    present = [k for k in KINDS if k in sensors]
    lists = {k: {c: v.tolist() for c, v in sensors[k].items()} for k in present}
    starts = np.cumsum([0] + [len(sensors[k]["t"]) for k in present])
    out: list[Measurement] = []
    for g in order.tolist():
        j = int(np.searchsorted(starts, g, side="right")) - 1
        k, row = present[j], g - int(starts[j])
        cols = lists[k]
        out.append(Measurement(t=cols["t"][row], kind=k, data={c: v[row] for c, v in cols.items() if c != "t"}))
    return out


def _run_estimators(
    road_map: RoadMap, sensors: dict[str, dict[str, np.ndarray]], t0: float, t1: float, rate_hz: float,
    estimators: dict[str, dict],
) -> tuple[dict[str, EstimateColumns], dict[str, float]]:
    """Feed measurements with m.t <= t_out, then sample estimate(t_out); truth is never passed.

    Also returns the mean wall-clock time of one update call per estimator, in microseconds.
    """
    stream = _merged(sensors)
    t_out = t0 + np.arange(int(np.floor((t1 - t0) * rate_hz + 1e-9)) + 1) / rate_hz
    result: dict[str, EstimateColumns] = {}
    compute_us: dict[str, float] = {}
    for key, params in estimators.items():
        cols = EstimateColumns()
        spent_ns = 0
        try:
            est: Estimator = get_estimator(key)()
            est.reset(road_map, params)
            i = 0
            for t in t_out.tolist():
                while i < len(stream) and stream[i].t <= t:
                    t_start = time.perf_counter_ns()
                    est.update(stream[i])
                    spent_ns += time.perf_counter_ns() - t_start
                    i += 1
                e = est.estimate(t)
                cols.t.append(t)
                cols.s.append(e.s)
                cols.v.append(e.v)
                cols.sigma_s.append(e.sigma_s)
                cols.display_s.append(e.s)  # no smoothing yet (T8.6)
                cols.mode.append(e.mode)
        except Exception as exc:
            raise EstimatorFailed(f"estimator {key} failed: {exc}") from exc
        result[key] = cols
        compute_us[key] = spent_ns / 1e3 / max(i, 1)
    return result, compute_us


def run_scenario(
    scenario: Scenario, estimators: dict[str, dict] | None = None, callout_k: float = 1.0,
) -> Trace:
    """Simulate all vehicles and sensors; run each requested estimator (registry id -> params) per vehicle."""
    estimators = estimators or {}
    rates, n_veh = scenario.rates_hz, len(scenario.vehicles)
    road_map = RoadMap(scenario.road)
    motion_ss, *vehicle_ss = np.random.SeedSequence(scenario.seed).spawn(1 + n_veh)
    motions = simulate_vehicles(scenario.vehicles, road_map, rates.imu, np.random.default_rng(motion_ss))
    vehicles: list[VehicleTrace] = []
    for veh, motion, ss in zip(scenario.vehicles, motions, vehicle_ss):
        r_imu, r_gnss, r_baro, r_mag, r_ble = (np.random.default_rng(c) for c in ss.spawn(len(KINDS)))
        preset, ph = load_preset(veh.phone.preset), veh.phone
        mount_path = MountPath(ph.mount, ph.handling_events, r_imu)  # shared by IMU and magnetometer
        sensors = {
            "imu": generate_imu(motion, ph.mount, ph.handling_events, preset, r_imu, path=mount_path),
            "gnss": generate_gnss(motion, road_map, scenario.gnss_env, preset, rates.gnss, r_gnss),
            "baro": generate_baro(motion, road_map, scenario.tunnel_env, preset, rates.baro, r_baro),
            "mag": generate_mag(
                motion, road_map, scenario.tunnel_env, preset, ph.mount, ph.handling_events, rates.mag, r_mag,
                path=mount_path,
            ),
            "ble": generate_ble(motion, road_map, scenario.beacons, r_ble),
        }
        sensors = {k: v for k, v in sensors.items() if len(v["t"]) > 0}
        meas = Measurements(**{k: _MODELS[k](**{c: a.tolist() for c, a in v.items()}) for k, v in sensors.items()})
        est, compute_us = (
            _run_estimators(road_map, sensors, float(motion.t[0]), float(motion.t[-1]), rates.output, estimators)
            if estimators else ({}, {})
        )
        truth = _truth(motion, road_map)
        tunnels = [(tn.id, tn.start_s, tn.end_s) for tn in road_map.tunnels]
        fix_t = sensors["gnss"]["t"].tolist() if "gnss" in sensors else []
        exits = [(x.id, x.s) for x in road_map.exits]
        callouts = {
            key: compute_callouts(e.t, e.s, e.sigma_s, truth.t, truth.s, exits, callout_k) for key, e in est.items()
        }
        metrics = {
            key: compute_metrics(e.t, e.s, e.sigma_s, e.display_s, truth.t, truth.s, tunnels, fix_t, callouts[key])
            for key, e in est.items()
        }
        for key in est:
            metrics[key]["compute_us_per_measurement"] = compute_us[key]
        ideal = ideal_times(truth.t, truth.s, exits)
        for key in est:
            if missed := missed_callouts(callouts[key], ideal):
                metrics[key]["missed_callouts"] = missed
        vehicles.append(VehicleTrace(
            id=veh.id, truth=truth, measurements=meas,
            events=_events(motion, road_map, ph.handling_events), estimates=est, callouts=callouts, metrics=metrics,
        ))
    return Trace(scenario_id=scenario.id, map=_map_columns(road_map), vehicles=vehicles)
