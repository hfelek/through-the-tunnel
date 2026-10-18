import json
from pathlib import Path

from fastapi.testclient import TestClient

from sim.api import main

SCENARIO = json.loads((Path(main.SCENARIOS) / "short_straight_500m.json").read_text())


def test_save_as_creates_rejects_and_never_overwrites(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(main, "SCENARIOS", tmp_path)
    client = TestClient(main.app)
    r = client.post("/api/scenarios", json={"id": "my_copy_1", "scenario": SCENARIO})
    assert r.status_code == 201
    assert json.loads((tmp_path / "my_copy_1.json").read_text())["id"] == "my_copy_1"
    assert client.post("/api/scenarios", json={"id": "Bad-Id", "scenario": SCENARIO}).status_code == 422
    assert client.post("/api/scenarios", json={"id": "my_copy_1", "scenario": SCENARIO}).status_code == 409
    assert client.post("/api/scenarios", json={"id": "bad_body", "scenario": {"id": "x"}}).status_code == 422
    assert [p.name for p in tmp_path.iterdir()] == ["my_copy_1.json"]
