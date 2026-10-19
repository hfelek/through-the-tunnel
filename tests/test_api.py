import json
from pathlib import Path

from fastapi.testclient import TestClient

from sim.api.main import app
from sim.estimators import register, unregister

client = TestClient(app)
SCENARIO = Path(__file__).resolve().parents[1] / "scenarios" / "short_straight_500m.json"


def test_get_endpoints() -> None:
    assert len(client.get("/api/scenarios").json()) == 15
    assert "baseline" in [e["id"] for e in client.get("/api/estimators").json()]
    assert {"budget", "flagship_2024"} <= set(client.get("/api/presets").json())
    assert client.get("/api/scenarios/short_straight_500m").json()["id"] == "short_straight_500m"
    assert client.get("/api/scenarios/nope").status_code == 404


def test_simulate_returns_trace_with_decimated_imu() -> None:
    r = client.post("/api/simulate", json={"scenario": json.loads(SCENARIO.read_text())})
    assert r.status_code == 200
    veh = r.json()["vehicles"][0]
    assert veh["id"] == "car1"
    assert "baseline" in veh["estimates"] and "baseline" in veh["callouts"] and "baseline" in veh["metrics"]
    tt = veh["truth"]["t"]
    assert 9 < (len(tt) - 1) / (tt[-1] - tt[0]) <= 10.5
    t = veh["measurements"]["imu"]["t"]
    assert 9 < (len(t) - 1) / (t[-1] - t[0]) <= 10.5


def test_invalid_inputs_rejected() -> None:
    sc = json.loads(SCENARIO.read_text())
    sc["road"]["tunnels"][0]["end_s"] = 1e6
    r = client.post("/api/simulate", json={"scenario": sc})
    assert r.status_code == 422 and "tunnels" in json.dumps(r.json())
    ok = json.loads(SCENARIO.read_text())
    r = client.post("/api/simulate", json={"scenario": ok, "estimators": {"nope": {}}})
    assert r.status_code == 422 and "nope" in json.dumps(r.json())
    assert client.get("/api/scenarios/..%2Fx").status_code in (404, 422)
    assert client.get("/api/scenarios/Bad.id").status_code == 422

    # parameter validation and estimator crashes become 422s
    sc = json.loads(SCENARIO.read_text())
    ests = {e["id"]: e for e in client.get("/api/estimators").json()}
    assert ests["baseline"]["params"]["n_speed_fixes"] == 3
    assert ests["baseline"]["constraints"]["n_speed_fixes"] == {"type": "int", "min": 1}
    for params, name in (({"nope": 1}, "nope"), ({"n_speed_fixes": 0}, "n_speed_fixes"), ({"gap_timeout_s": 0}, "gap_timeout_s")):
        r = client.post("/api/simulate", json={"scenario": sc, "estimators": {"baseline": params}})
        assert r.status_code == 422 and name in r.json()["detail"]

    @register
    class Crashy:
        id, label = "crashy", "Crashy"

        def reset(self, road, params):
            raise RuntimeError("boom")

    try:
        r = client.post("/api/simulate", json={"scenario": sc, "estimators": {"crashy": {}}})
    finally:
        unregister("crashy")
    assert r.status_code == 422 and r.json()["detail"] == "estimator crashy failed: boom"
