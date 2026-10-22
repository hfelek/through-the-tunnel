import csv

from sim.eval import montecarlo, summary


def test_montecarlo_csv_resume_and_summary(tmp_path):
    args = ["--seeds", "2", "--scenarios", "short_straight_500m", "--jobs", "1", "--out", str(tmp_path)]
    montecarlo.main(args)  # N = 2, one short scenario, all four estimators, written to a temporary directory
    path = tmp_path / "runs.csv"
    rows = list(csv.DictReader(path.open()))
    assert list(rows[0]) == montecarlo.COLUMNS and len(rows) == 2 * 4  # 2 seeds x 4 estimators, one vehicle
    assert {r["seed"] for r in rows} != {rows[0]["seed"]}  # the seeds differ
    assert all(r["rmse_in_tunnel_m"] != "" and r["exit_error_m_t0"] != "" for r in rows)
    assert all(r["callout_err_500_s"] == "" and r["missed_callouts"] == "" for r in rows)  # exit outside the tunnel: empty
    montecarlo.main(args)  # resume: every (scenario, seed, estimator) is finished, nothing is added
    assert len(list(csv.DictReader(path.open()))) == len(rows)
    summary.main(["--out", str(tmp_path), "--no-plots"])
    text = (tmp_path / "summary.md").read_text()
    assert "| short_straight_500m | pf |" in text and "## Callout timing" in text
