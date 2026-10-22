import csv

from sim.eval import sweep


def test_bias_sweep_csv_and_figures(tmp_path):
    sweep.main(["--sweep", "accel_bias", "--values", "1", "5", "--seeds", "2", "--scenarios", "short_straight_500m",
                "--estimators", "baseline", "ekf_zupt", "--jobs", "1", "--out", str(tmp_path)])
    rows = list(csv.DictReader((tmp_path / "accel_bias.csv").open()))
    assert len(rows) == 2 * 2 * 2 and {r["variant"] for r in rows} == {"x1", "x5"}  # 2 values x 2 seeds x 2 estimators
    sweep.main(["--figures", "--out", str(tmp_path)])  # tables and figures from the CSV, no simulation
    assert (tmp_path / "accel_bias_summary.md").exists() and (tmp_path / "accel_bias_exit_error.png").exists()
