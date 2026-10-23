"""Figure for the write-up: along-track error of the baseline, EKF and PF on the real drive with the default outage window.

    python tools/plot_real_replay.py        # writes docs/results/real_replay.png

Left: the EKF's default offset drift (bias_rw 5e-4). Right: 20x larger (0.01). Calibration is relaxed for real roads in both.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sim.api.real import DEFAULT_OUTAGE_S
from sim.realdata.replay import REAL_DEFAULTS, replay
from sim.realdata.sensor_logger import DEFAULT_SPAN_S, load_recording

OUT = Path(__file__).resolve().parents[1] / "docs" / "results" / "real_replay.png"
COLORS = {"baseline": "#2563eb", "ekf": "#dc2626", "pf": "#d97706"}
LABELS = {"baseline": "Baseline", "ekf": "EKF", "pf": "PF"}


def main() -> None:
    trace = load_recording("car_mounted")
    t0 = DEFAULT_SPAN_S[0]
    a, b = DEFAULT_OUTAGE_S
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6), sharey=True)
    for ax, bias_rw in zip(axes, (5e-4, 0.01)):
        est = {"baseline": {}, "ekf": {**REAL_DEFAULTS, "bias_rw": bias_rw}, "pf": {**REAL_DEFAULTS, "bias_rw": bias_rw}}
        veh = replay(trace, a - t0, b - t0, est).vehicles[0]
        ax.axvspan(a, b, color="#374151", alpha=0.14, label="GNSS removed (artificial tunnel)")
        for key, e in veh.estimates.items():
            ax.plot([t + t0 for t in e.t], veh.metrics[key]["error"], color=COLORS[key], label=LABELS[key], lw=1.4)
        ax.axhline(0, color="#6b7280", lw=0.8)
        ax.set_title(f"bias_rw = {bias_rw:g}")
        ax.set_xlabel("recording time (s)")
        ax.set_xlim(a - 60, b + 60)
    axes[0].set_ylabel("along-track error (m)")
    axes[0].legend(loc="lower left", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT, dpi=140)


if __name__ == "__main__":
    main()
