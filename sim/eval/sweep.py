"""Parameter sweeps (T9.2): the Monte Carlo machinery with one varied simulator parameter.

    python -m sim.eval.sweep --sweep accel_bias --seeds 30     (runs; resumable CSV under docs/results/sweeps/)
    python -m sim.eval.sweep --figures                         (tables and figures from the CSVs, no simulation)

`accel_bias`: the simulated phone's accelerometer bias (constant part and drift, A14) times 0.5, 1, 2, 3, 5; the estimators
keep assuming the original phone. `tunnel_length`: a straight flat tunnel of 0.5-5 km (derived from short_straight_500m, the
exit 300 m after the tunnel).
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np

from sim.eval import montecarlo as mc
from sim.eval import summary

SWEEPS: dict[str, dict] = {
    "accel_bias": {
        "setting": "accel_bias_scale", "values": (0.5, 1, 2, 3, 5), "label": lambda v: f"x{v:g}", "xlabel": "accelerometer bias x",
        "scenarios": ("speed_changes_3km", "stop_and_go_3km", "curved_5km_exit_inside", "hard_brake_inside"),
        "estimators": ("baseline", "ekf_zupt", "pf"),
    },
    "tunnel_length": {
        "setting": "tunnel_km", "values": (0.5, 1, 2, 3, 5), "label": lambda v: f"{v:g} km", "xlabel": "tunnel length (km)",
        "scenarios": ("short_straight_500m",), "estimators": mc.ESTIMATORS,
    },
}
SWEEP_DIR = mc.RESULTS / "sweeps"


def _value(label: str) -> float:
    return float(re.search(r"[\d.]+", label).group())


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sweep", choices=sorted(SWEEPS), help="which sweep to run")
    ap.add_argument("--seeds", type=int, default=30, help="seeds per scenario and value (default 30)")
    ap.add_argument("--values", nargs="+", type=float, help="override the parameter values")
    ap.add_argument("--scenarios", nargs="+")
    ap.add_argument("--estimators", nargs="+")
    ap.add_argument("--jobs", type=int, default=0, help="worker processes (default: all cores)")
    ap.add_argument("--out", type=Path, default=SWEEP_DIR, help="output directory (default docs/results/sweeps)")
    ap.add_argument("--figures", action="store_true", help="only regenerate tables and figures from the CSVs")
    args = ap.parse_args(argv)
    if args.figures:
        figures(args.out)
        return
    if not args.sweep:
        ap.error("--sweep or --figures is required")
    sw = SWEEPS[args.sweep]
    variants = {sw["label"](v): {sw["setting"]: v} for v in (args.values or sw["values"])}
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / f"{args.sweep}.csv"
    tasks = mc.plan_tasks(args.scenarios or list(sw["scenarios"]), args.estimators or list(sw["estimators"]), variants,
                          args.seeds, mc._read_done(path), mc.git_hash())
    mc.execute(tasks, path, args.jobs)


def _exit_abs(rows: list[dict[str, str]]) -> np.ndarray:
    return np.abs(np.concatenate([summary._nums(rows, f"exit_error_m_t{i}") for i in range(mc.MAX_TUNNELS)]))


def figures(out: Path) -> None:
    """Summary table plus two figures per sweep CSV: median |exit error| and mean consistency against the value."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    for name, sw in SWEEPS.items():
        path = out / f"{name}.csv"
        if not path.exists():
            continue
        rows = summary.read_rows(path)
        summary.write_summary(rows, out / f"{name}_summary.md", f"Sweep: {name}")
        scenarios = sorted({r["scenario"] for r in rows})
        estimators = [e for e in mc.ESTIMATORS if any(r["estimator"] == e for r in rows)]
        for fname, title, floor in (("exit_error", "median |exit error| (m)\nlog scale, clipped at 0.1 m", summary.FLOOR_M),
                                    ("consistency", "mean consistency (%)", None)):
            fig, axes = plt.subplots(1, len(scenarios), figsize=(4.2 * len(scenarios), 3.6), squeeze=False)
            for ax, scen in zip(axes[0], scenarios, strict=True):
                for est in estimators:
                    pts = []
                    for variant in sorted({r["variant"] for r in rows}, key=_value):
                        g = [r for r in rows if r["scenario"] == scen and r["estimator"] == est and r["variant"] == variant]
                        if not g:
                            continue
                        y = (max(float(np.median(_exit_abs(g))), floor) if floor else float(summary._nums(g, "consistency_pct").mean()))
                        pts.append((_value(variant), y))
                    if pts:
                        ax.plot(*zip(*pts, strict=True), marker="o", label=est)
                ax.set_title(scen, fontsize=9)
                ax.set_xlabel(sw["xlabel"])
                if floor:
                    ax.set_yscale("log")
            axes[0][0].set_ylabel(title)
            axes[0][0].legend(fontsize=8)
            fig.tight_layout()
            fig.savefig(out / f"{name}_{fname}.png", dpi=130)
            plt.close(fig)
        print(f"wrote {name} figures in {out}")


if __name__ == "__main__":
    main()
