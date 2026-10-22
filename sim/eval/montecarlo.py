"""Monte Carlo evaluation (T9.1): every scenario x seed x estimator, in parallel processes, one CSV row per run.

    python -m sim.eval.montecarlo [--seeds 50] [--scenarios a b] [--estimators ekf pf] [--jobs 4] [--study a30]

Rows are appended to the CSV as each task finishes, so an interrupted run resumes and skips finished
(scenario, variant, seed, estimator) rows. The summary and the plots are made from the CSV by `sim.eval.summary`.
"""
from __future__ import annotations

import argparse
import csv
import signal
import subprocess
import time
from multiprocessing import Pool
from pathlib import Path
from typing import Any

import numpy as np

import sim.estimators  # noqa: F401  (registers the estimators)
from sim.contracts.scenario import Scenario, load_scenario
from sim.estimators.alignment import Aligner, G
from sim.estimators.ekf import EkfEstimator
from sim.eval.callouts import DISTANCES_M

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ROOT / "scenarios"
RESULTS = ROOT / "docs" / "results"

ESTIMATORS = ("baseline", "ekf", "ekf_zupt", "pf")
DEFAULT_C1 = Aligner.default_params["tilt_gyro_c1_deg_per_s"]  # A30 default, read before any worker overrides it
MAX_TUNNELS = 3  # exit-error columns per row: one per tunnel index
COUNTERS = ("gate_resets", "beacon_updates", "zupt_applied", "zupt_gated", "bias_gated")  # EKF counters; empty where absent

COLUMNS = [
    "scenario", "vehicle", "estimator", "variant", "seed", "git",
    "rmse_in_tunnel_m", "consistency_pct", "us_per_measurement", *COUNTERS, "accel_use_pct",
    *(f"exit_error_m_t{i}" for i in range(MAX_TUNNELS)),
    *(f"recovery_time_s_t{i}" for i in range(MAX_TUNNELS)), "max_display_jump_m",
    *(f"callout_err_{d}_s" for d in DISTANCES_M), "missed_callouts",
]

# Side studies (same script): a variant is a dict of settings applied inside the worker; no estimator code changes.
#   aligner_c1: A30 `tilt_gyro_c1_deg_per_s` (the EKF builds its aligner with the defaults, so the default is overridden)
#   trace_accel: record the share of IMU samples after the put-back on which the EKF used the accelerometer
#   beacon_sigma: EKF parameter, passed as an estimator parameter
STUDIES: dict[str, dict[str, Any]] = {
    "a30": {  # c1 = 1e-9 means no tilt uncertainty growth; the EKF then trusts the accelerometer after the put-back
        "csv": "a30_runs.csv",
        "scenarios": ("phone_handled_mid_tunnel", "phone_in_hand_2min"),  # both end their hand event in the tunnel
        "estimators": ("ekf_zupt",),
        "variants": {f"c1={v}": {"aligner_c1": c1, "trace_accel": True} for v, c1 in (("1e-9", 1e-9), ("0.02", 0.02), ("0.03", 0.03))},
    },
    "beacon_sigma": {
        "csv": "beacon_sigma_runs.csv",
        "scenarios": ("beacons_5km",),
        "estimators": ("ekf_zupt",),
        "variants": {f"sigma={v}": {"beacon_sigma": float(v)} for v in (5, 10, 15)},
    },
}
MAIN_STUDY = {"csv": "runs.csv", "variants": {"": {}}}


def derive_seed(scenario_seed: int, k: int) -> int:
    """Seed k of a scenario: k = 0 is the scenario's own seed, the others come from a SeedSequence (deterministic)."""
    if k == 0:
        return scenario_seed
    return int(np.random.SeedSequence([scenario_seed, k]).generate_state(1)[0] & 0x7FFFFFFF)


def git_hash() -> str:
    """Short commit hash, plus "-dirty" when tracked or new files outside docs/results differ from it."""
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False).stdout.strip()
    head = git("rev-parse", "--short", "HEAD") or "unknown"
    return head + ("-dirty" if git("status", "--porcelain", "--", ".", ":!docs/results") else "")


def scaled_preset(preset: Any, factor: float) -> Any:
    """Copy of a phone preset with the accelerometer bias (constant part and drift, A14) multiplied; estimators never see it."""
    p = preset.model_copy(deep=True)
    p.accel.initial_bias_max.value *= factor
    p.accel.bias_random_walk.value *= factor
    return p


def with_tunnel_length(sc: Scenario, km: float, tail_m: float = 1500.0, exit_after_m: float = 300.0) -> Scenario:
    """Straight flat scenario with the first tunnel `km` long, `tail_m` of road after it and the exit `exit_after_m` after it."""
    t = sc.road.tunnels[0]
    end = t.start_s + 1000.0 * km
    raw = sc.model_dump()
    raw["road"]["segments"] = [{"type": "straight", "length_m": length, "grade_pct": 0}
                               for length in (t.start_s, end - t.start_s, tail_m)]
    raw["road"]["tunnels"] = [{"id": t.id, "start_s": t.start_s, "end_s": end}]
    raw["road"]["exits"] = [{**raw["road"]["exits"][0], "s": end + exit_after_m}]
    raw["road"]["speed_limits"] = [{**sl, "to_s": end + tail_m} for sl in raw["road"]["speed_limits"]]
    return Scenario.model_validate(raw)  # validates: tunnel, exit and limits stay on the road


def exit_in_tunnel(sc: Scenario) -> str | None:
    """Id of the first exit that lies inside a tunnel; the callout columns are only filled for such scenarios."""
    for ex in sc.road.exits:
        if any(t.start_s <= ex.s <= t.end_s for t in sc.road.tunnels):
            return ex.id
    return None


def watch_accel_use(ekf: Any) -> list[tuple[float, bool]]:
    """Wrap `ekf.update` (the instance only, no estimator code changes) to log, per IMU sample from the first put-back
    on, whether the EKF integrated the accelerometer. The rule is the one in ekf.py: a valid aligned sample and either
    a current fix or sqrt(P_bias) <= accel_trust_sigma_b, where P_bias includes the put-back inflation (G * sigma_tilt)^2."""
    log: list[tuple[float, bool]] = []
    update = ekf.update
    state = {"put_back": False}

    def wrapped(m: Any) -> None:
        if m.kind != "imu":
            update(m)
            return
        p_bias = float(ekf.P[2, 2])  # before the update: the put-back inflation is added inside it
        update(m)
        a = getattr(ekf, "aligned", None)
        if a is None:
            return
        if a.mount_changed:
            state["put_back"] = True
            p_bias += (G * a.sigma_tilt) ** 2
        if state["put_back"]:
            current = ekf._t_acc is not None and m.t - ekf._t_acc <= ekf.gnss_timeout_s
            log.append((m.t, bool(a.valid and (current or np.sqrt(p_bias) <= ekf.accel_trust_sigma_b))))

    ekf.update = wrapped
    return log


def accel_use_pct(log: list[tuple[float, bool]], trace_vehicle: Any) -> float | str:
    """Share (%) of the logged IMU samples, from the put-back to the tunnel exit, that used the accelerometer."""
    if not log:
        return ""
    t0 = log[0][0]
    exits = [e.t for e in trace_vehicle.events if e.type == "tunnel_exit" and e.t > t0]
    t_end = exits[0] if exits else log[-1][0]
    used = [u for t, u in log if t <= t_end]
    return 100.0 * sum(used) / len(used) if used else ""


def _cell(x: Any) -> Any:
    return "" if x is None else x


def make_rows(sc: Scenario, trace: Any, counters: dict[tuple[int, str], dict[str, Any]], seed: int,
              variant: str, git: str) -> list[dict[str, Any]]:
    """One row per vehicle and estimator from a finished run."""
    tunnel_ids = [t.id for t in sc.road.tunnels]
    exit_id = exit_in_tunnel(sc)
    rows = []
    for vi, veh in enumerate(trace.vehicles):
        for key, m in veh.metrics.items():
            row: dict[str, Any] = dict.fromkeys(COLUMNS, "")
            row.update(scenario=sc.id, vehicle=veh.id, estimator=key, variant=variant, seed=seed, git=git,
                       rmse_in_tunnel_m=_cell(m.get("rmse_in_tunnel_m")), consistency_pct=_cell(m.get("consistency_pct")),
                       us_per_measurement=_cell(m.get("compute_us_per_measurement")))
            row.update({c: v for c, v in counters.get((vi, key), {}).items()})
            for i, tid in enumerate(tunnel_ids[:MAX_TUNNELS]):
                row[f"exit_error_m_t{i}"] = _cell(m.get("exit_error_m", {}).get(tid))
                row[f"recovery_time_s_t{i}"] = _cell(m.get("recovery_time_s", {}).get(tid))  # empty = never recovered
            row["max_display_jump_m"] = _cell(m.get("max_display_jump_m"))
            if exit_id is not None:  # callout timing t - t_ideal (positive = late); a missed callout leaves its cell empty
                timing = m.get("callout_timing_error_s", {}).get(exit_id, {})
                for d in DISTANCES_M:
                    row[f"callout_err_{d}_s"] = _cell(timing.get(str(d)))
                row["missed_callouts"] = len(m.get("missed_callouts", []))
            rows.append(row)
    return rows


def run_task(task: tuple[str, str, dict, int, int, tuple[str, ...], str]) -> list[dict[str, Any]]:
    """One (scenario, variant, seed) with the missing estimators; runs inside a worker process."""
    from sim import runner

    name, variant, settings, k, _, estimators, git = task
    # the live-demo API passes the scenario being edited in the UI instead of a file name
    sc = Scenario.model_validate(settings["scenario"]) if "scenario" in settings else load_scenario(SCENARIOS / f"{name}.json")
    seed = derive_seed(sc.seed, k)
    sc = sc.model_copy(update={"seed": seed})  # the seed changes everything random in the scenario
    if "tunnel_km" in settings:
        sc = with_tunnel_length(sc, settings["tunnel_km"])
    params: dict[str, dict] = {e: dict(settings.get("params", {}).get(e, {})) for e in estimators}
    if "pf" in params and k > 0:
        params["pf"]["seed"] = seed % (2**31)  # seed 0 keeps the pf's default seed, so it reproduces earlier single runs
    if "beacon_sigma" in settings:
        for e, p in params.items():
            if e != "baseline":
                p["beacon_sigma"] = settings["beacon_sigma"]
    if "aligner_c1" in settings:
        Aligner.default_params["tilt_gyro_c1_deg_per_s"] = settings["aligner_c1"]  # A30
    else:
        Aligner.default_params["tilt_gyro_c1_deg_per_s"] = DEFAULT_C1  # a worker may have run a variant before

    made: list[tuple[str, Any]] = []
    watched: dict[int, list[tuple[float, bool]]] = {}
    real = runner.get_estimator

    def spy(key: str):  # records the instances the runner builds, to read their counters afterwards
        cls = real(key)

        def make():
            inst = cls()
            made.append((key, inst))
            if settings.get("trace_accel") and isinstance(inst, EkfEstimator):  # the aligner only exists after reset()
                watched[id(inst)] = watch_accel_use(inst)
            return inst
        return make

    runner.get_estimator = spy
    real_preset = runner.load_preset
    if "accel_bias_scale" in settings:  # the simulated phone changes, the filters keep assuming the original one
        runner.load_preset = lambda name: scaled_preset(real_preset(name), settings["accel_bias_scale"])
    try:
        trace = runner.run_scenario(sc, params)
    finally:
        runner.get_estimator = real
        runner.load_preset = real_preset
    seen: dict[str, int] = {}
    counters: dict[tuple[int, str], dict[str, Any]] = {}
    for key, inst in made:  # the runner builds the estimators vehicle by vehicle
        vi = seen.get(key, 0)
        seen[key] = vi + 1
        src = getattr(inst, "ekf", inst)  # the particle filter wraps an EKF
        counters[(vi, key)] = {c: getattr(src, c) for c in COUNTERS if hasattr(src, c)}
        if id(inst) in watched:
            counters[(vi, key)]["accel_use_pct"] = accel_use_pct(watched[id(inst)], trace.vehicles[vi])
    return make_rows(sc, trace, counters, seed, variant, git)


def ignore_sigint() -> None:
    """Pool initializer: Ctrl+C reaches only the parent, which then stops the pool (no traceback per worker)."""
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def timed_task(task: tuple) -> tuple[list[dict[str, Any]], float]:
    """run_task plus its wall time in seconds (the API extrapolates its runtime from the first tasks)."""
    t0 = time.perf_counter()
    rows = run_task(task)
    return rows, time.perf_counter() - t0


def inline_tasks(sc: Scenario, params: dict[str, dict], n_seeds: int) -> list[tuple]:
    """One task per seed for a scenario given as an object (not a file), with the estimator parameters as they are in the UI."""
    git = git_hash()
    settings = {"scenario": sc.model_dump(mode="json"), "params": params}
    return [(sc.id, "", settings, k, derive_seed(sc.seed, k), tuple(params), git) for k in range(n_seeds)]


def _read_done(path: Path) -> set[tuple[str, str, int, str]]:
    if not path.exists():
        return set()
    with path.open(newline="") as f:
        return {(r["scenario"], r["variant"], int(r["seed"]), r["estimator"]) for r in csv.DictReader(f)}


def _append(path: Path, rows: list[dict[str, Any]]) -> None:
    new = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        if new:
            w.writeheader()
        w.writerows(rows)
        f.flush()


def plan_tasks(scenarios: list[str], estimators: list[str], variants: dict[str, dict], n_seeds: int,
               done: set[tuple[str, str, int, str]], git: str) -> list[tuple]:
    tasks = []
    for name in scenarios:
        base_seed = load_scenario(SCENARIOS / f"{name}.json").seed
        for variant, settings in variants.items():
            for k in range(n_seeds):
                seed = derive_seed(base_seed, k)
                todo = tuple(e for e in estimators if (name, variant, seed, e) not in done)
                if todo:
                    tasks.append((name, variant, settings, k, seed, todo, git))
    return tasks


def execute(tasks: list[tuple], path: Path, jobs: int) -> None:
    """Run the tasks (in worker processes unless jobs == 1) and append each finished task's rows to the CSV."""
    print(f"{len(tasks)} tasks to run ({path})", flush=True)
    t0 = time.time()
    if jobs == 1:  # inline: easier to debug, and no process start-up in the smoke tests
        finished = map(run_task, tasks)
        pool = None
    else:
        pool = Pool(jobs or None, initializer=ignore_sigint)
        finished = pool.imap_unordered(run_task, tasks)
    try:
        for i, rows in enumerate(finished, 1):
            _append(path, rows)
            print(f"[{i}/{len(tasks)}] {rows[0]['scenario']} {rows[0]['variant']} seed {rows[0]['seed']} "
                  f"({time.time() - t0:.0f} s)", flush=True)
    finally:
        if pool is not None:
            pool.terminate()


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", type=int, default=50, help="seeds per scenario (default 50)")
    ap.add_argument("--scenarios", nargs="+", help="subset of scenario ids (default: all files in scenarios/)")
    ap.add_argument("--estimators", nargs="+", help=f"subset of {list(ESTIMATORS)}")
    ap.add_argument("--jobs", type=int, default=0, help="worker processes (default: all cores)")
    ap.add_argument("--study", choices=sorted(STUDIES), help="side study instead of the main run")
    ap.add_argument("--out", type=Path, default=RESULTS, help="results directory (default docs/results)")
    args = ap.parse_args(argv)

    study = STUDIES[args.study] if args.study else MAIN_STUDY
    scenarios = args.scenarios or list(study.get("scenarios") or sorted(p.stem for p in SCENARIOS.glob("*.json")))
    estimators = args.estimators or list(study.get("estimators", ESTIMATORS))
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / study["csv"]
    tasks = plan_tasks(scenarios, estimators, study["variants"], args.seeds, _read_done(path), git_hash())
    execute(tasks, path, args.jobs)


if __name__ == "__main__":
    main()
