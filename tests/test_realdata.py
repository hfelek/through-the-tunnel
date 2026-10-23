"""Real-drive loader and API smoke tests (T10.5a); skipped when the recording is not in the checkout."""
import numpy as np
import pytest
from fastapi.testclient import TestClient

from sim.api.main import app
from sim.realdata.sensor_logger import REAL_DIR, load_arrays

pytestmark = pytest.mark.skipif(not (REAL_DIR / "car_mounted" / "Location.csv").is_file(), reason="no recording")


def test_ios_signs_and_units() -> None:
    imu, g = load_arrays(REAL_DIR / "car_mounted", 110, 830)
    assert 9.3 < np.mean(imu["az"]) < 10.1  # face-up phone reads +g after the iOS conversion (iOS reports -g)
    moving = g["speed"] > 3
    rate = np.gradient(np.unwrap(g["course"]), g["t"])  # GNSS course rate, ENU (CCW positive)
    gz = np.array([imu["gz"][(imu["t"] >= a - 0.5) & (imu["t"] < a + 0.5)].mean() for a in g["t"]])
    assert np.corrcoef(rate[moving], gz[moving])[0, 1] > 0.5  # a left turn gives a positive gyro z, like the course rate


def test_real_run_baseline() -> None:
    client = TestClient(app)
    assert client.get("/api/real").json()[0]["id"] == "car_mounted"
    r = client.post("/api/real/car_mounted/run", json={"estimators": {"baseline": {}}})
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "real" and [t["id"] for t in body["map"]["tunnels"]] == ["T1"]
    assert body["vehicles"][0]["metrics"]["baseline"]["exit_error_m"]["T1"] < -100  # the baseline stops short (about -563 m)
    assert body["vehicles"][0]["metrics"]["baseline"]["recovery_time_s"] == {}  # undefined for a replay, not 0 s
    assert client.post("/api/real/car_mounted/run", json={"outage_start_s": 120}).status_code == 422  # under 60 s of GNSS
