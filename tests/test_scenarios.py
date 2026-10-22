from pathlib import Path

from sim.contracts.scenario import load_scenario
from sim.runner import run_scenario

SCENARIO_DIR = Path(__file__).resolve().parents[1] / "scenarios"


def test_every_scenario_validates_and_runs():
    files = sorted(SCENARIO_DIR.glob("*.json"))
    failures = []
    for path in files:
        try:
            sc = load_scenario(path)
            assert sc.id == path.stem, f"id '{sc.id}' != file name"
            assert sc.description.strip(), "empty description"
            assert sc.title.strip(), "empty title"
            run_scenario(sc)
        except Exception as e:  # noqa: BLE001 - collect every failure, assert once
            failures.append(f"{path.name}: {type(e).__name__}: {e}")
    assert len(files) >= 15
    assert not failures, "\n".join(failures)
