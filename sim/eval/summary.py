"""Summary tables and plots from the Monte Carlo CSV files (T9.1). Never reruns a simulation.

    python -m sim.eval.summary [--out docs/results] [--no-plots]

Writes summary.md and the PNG plots for runs.csv, and a_summary for each side-study CSV that exists.
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

from sim.eval.callouts import DISTANCES_M
from sim.eval.montecarlo import ESTIMATORS, MAIN_STUDY, MAX_TUNNELS, RESULTS, STUDIES

FLOOR_M = 0.1  # the log-scale overview clips |exit error| at this floor (zero cannot be drawn on a log axis)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def _nums(rows: list[dict[str, str]], col: str) -> np.ndarray:
    return np.array([float(r[col]) for r in rows if r[col] != ""], dtype=float)


def _stat(values: np.ndarray, fn, fmt: str = "{:.1f}") -> str:
    return fmt.format(fn(values)) if len(values) else "–"


def _p90(v: np.ndarray) -> float:
    return float(np.percentile(v, 90))


def _p95(v: np.ndarray) -> float:
    return float(np.percentile(v, 95))


def _groups(rows: list[dict[str, str]]) -> dict[tuple[str, str, str], list[dict[str, str]]]:
    """Rows by (variant, scenario, estimator), in a stable order."""
    out: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        out[(r["variant"], r["scenario"], r["estimator"])].append(r)
    order = {e: i for i, e in enumerate(ESTIMATORS)}
    return dict(sorted(out.items(), key=lambda kv: (kv[0][0], kv[0][1], order.get(kv[0][2], 99))))


def n_tunnels(rows: list[dict[str, str]]) -> int:
    """Tunnels of a scenario, from the exit-error columns that are ever filled."""
    return max((i + 1 for i in range(MAX_TUNNELS) if any(r[f"exit_error_m_t{i}"] != "" for r in rows)), default=1)


def has_variants(rows: list[dict[str, str]]) -> bool:
    return any(r["variant"] != "" for r in rows)


def _recovery_cells(g: list[dict[str, str]], i: int, first: bool) -> list[str]:
    """Recovery per tunnel (an empty cell = never recovered, counted); the display jump is per run, so on the first tunnel row."""
    rec = _nums(g, f"recovery_time_s_t{i}")
    not_rec = sum(1 for r in g if r[f"exit_error_m_t{i}"] != "" and r[f"recovery_time_s_t{i}"] == "")
    jump = _nums(g, "max_display_jump_m")
    return [_stat(rec, np.median), _stat(rec, _p90), str(not_rec),
            _stat(jump, np.median) if first else "", _stat(jump, np.max) if first else ""]


def accuracy_table(rows: list[dict[str, str]]) -> list[str]:
    head = ["Scenario", "Estimator", "Tunnel", "Runs", "Median abs. exit error (m)", "p90 abs. exit error (m)",
            "p95 abs. exit error (m)", "Max abs. exit error (m)",
            "Median recovery (s)", "p90 recovery (s)", "Not recovered", "Median max display jump (m)", "Max display jump (m)", "Median RMSE (m)", "Mean consistency (%)", "Missed callouts", "Median time (µs/meas.)"]
    use = any(r["accel_use_pct"] != "" for r in rows)  # only the A30 study records it
    if use:
        head.append("Mean accelerometer use after put-back (%)")
    var = has_variants(rows)
    if var:
        head.insert(0, "Variant")
    lines = ["| " + " | ".join(head) + " |", "|" + " --- |" * len(head)]
    for (variant, scen, est), g in _groups(rows).items():
        for i in range(n_tunnels(g)):
            err = np.abs(_nums(g, f"exit_error_m_t{i}"))
            first = i == 0
            cells = [scen, est, f"T{i}" if n_tunnels(g) > 1 else "", str(len(g)), _stat(err, np.median), _stat(err, _p90),
                     _stat(err, _p95), _stat(err, np.max),
                     *_recovery_cells(g, i, first),
                     _stat(_nums(g, "rmse_in_tunnel_m"), np.median) if first else "",
                     _stat(_nums(g, "consistency_pct"), np.mean) if first else "",
                     str(int(_nums(g, "missed_callouts").sum())) if first and len(_nums(g, "missed_callouts")) else "–",
                     _stat(_nums(g, "us_per_measurement"), np.median) if first else ""]
            if use:
                cells.append(_stat(_nums(g, "accel_use_pct"), np.mean) if first else "")
            lines.append("| " + " | ".join(([variant] if var else []) + cells) + " |")
    return lines


def callout_table(rows: list[dict[str, str]]) -> list[str]:
    """Timing error t - t_ideal per callout distance (positive = late); only scenarios with an exit inside a tunnel."""
    head = ["Scenario", "Estimator"] + [f"{d} m: median / median abs. / p90 abs. (s)" for d in DISTANCES_M]
    var = has_variants(rows)
    if var:
        head.insert(0, "Variant")
    lines = ["| " + " | ".join(head) + " |", "|" + " --- |" * len(head)]
    for (variant, scen, est), g in _groups(rows).items():
        if not _nums(g, "missed_callouts").size:
            continue  # no exit inside a tunnel: the callout columns are empty
        cells = [scen, est]
        for d in DISTANCES_M:
            v = _nums(g, f"callout_err_{d}_s")
            cells.append(" / ".join((f"{np.median(v):+.1f}", f"{np.median(np.abs(v)):.1f}", f"{_p90(np.abs(v)):.1f}")) if len(v) else "–")
        lines.append("| " + " | ".join(([variant] if var else []) + cells) + " |")
    return lines


def write_summary(rows: list[dict[str, str]], path: Path, title: str) -> None:
    n_seeds = len({(r["scenario"], r["seed"]) for r in rows})
    commits = sorted({r["git"] for r in rows})
    git_line = f"Git hashes in the CSV: {', '.join(f'`{c}`' for c in commits)}"  # a mixed set means rows from different commits
    text = "\n".join([
        f"# {title}", "",
        (f"{len(rows)} rows, commit {', '.join(commits)}. `Runs` counts rows (vehicle x seed). Exit error is signed in "
         "the CSV; the table uses its absolute value (per tunnel where a scenario has several). Consistency is the share "
         "of tunnel samples with |error| < 2 sigma. Timing error is t - t_ideal (positive = late). Time per measurement "
         "was measured with several processes running in parallel, so only the ratios are meaningful."), "",
        "## Accuracy", "", git_line, "", *accuracy_table(rows), "",
        "## Callout timing", "", git_line, "", *callout_table(rows), "",
    ])
    path.write_text(text)
    print(f"wrote {path} ({n_seeds} scenario-seed pairs)")


def plots(rows: list[dict[str, str]], out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    groups = _groups(rows)
    scenarios = sorted({s for _, s, _ in groups})
    estimators = [e for e in ESTIMATORS if any(k[2] == e for k in groups)]
    for scen in scenarios:  # box plot of |exit error| per estimator (and tunnel)
        data, labels = [], []
        for est in estimators:
            g = groups.get(("", scen, est), [])
            for i in range(n_tunnels(g) if g else 1):
                v = np.abs(_nums(g, f"exit_error_m_t{i}")) if g else np.array([])
                if len(v):
                    data.append(v)
                    labels.append(est + (f" T{i}" if n_tunnels(g) > 1 else ""))
        if not data:
            continue
        fig, ax = plt.subplots(figsize=(max(4.0, 1.3 * len(data)), 3.6))
        ax.boxplot(data, tick_labels=labels)
        ax.set_ylabel("|exit error| (m)")
        ax.set_title(f"{scen}: |exit error| over {len(data[0])} seeds")
        fig.tight_layout()
        fig.savefig(out / f"exit_error_{scen}.png", dpi=130)
        plt.close(fig)
    fig, ax = plt.subplots(figsize=(max(8.0, 0.9 * len(scenarios)), 4.5))  # overview, log scale
    width = 0.8 / max(len(estimators), 1)
    for j, est in enumerate(estimators):
        med = []
        for scen in scenarios:
            g = groups.get(("", scen, est), [])
            v = np.concatenate([np.abs(_nums(g, f"exit_error_m_t{i}")) for i in range(n_tunnels(g))]) if g else np.array([])
            med.append(max(float(np.median(v)), FLOOR_M) if len(v) else np.nan)  # clipped at the floor
        ax.bar(np.arange(len(scenarios)) + j * width, med, width, label=est)
    ax.set_yscale("log")
    ax.set_xticks(np.arange(len(scenarios)) + 0.4 - width / 2, scenarios, rotation=60, ha="right")
    ax.set_ylabel(f"median |exit error| (m)\nlog scale, clipped at {FLOOR_M} m")  # two lines: one long line was cut off
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "overview_median_exit_error.png", dpi=130)
    plt.close(fig)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=RESULTS, help="results directory (default docs/results)")
    ap.add_argument("--no-plots", action="store_true")
    args = ap.parse_args(argv)
    main_csv = args.out / MAIN_STUDY["csv"]
    if main_csv.exists():
        rows = read_rows(main_csv)
        write_summary(rows, args.out / "summary.md", "Monte Carlo summary")
        if not args.no_plots:
            plots(rows, args.out)
    for name, study in STUDIES.items():
        path = args.out / study["csv"]
        if path.exists():
            write_summary(read_rows(path), args.out / f"{name}_summary.md", f"Side study: {name}")


if __name__ == "__main__":
    main()
