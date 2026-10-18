import numpy as np

from sim.contracts.scenario import Beacons, Road
from sim.sensors import ble
from sim.sensors.ble import beacon_positions, generate_ble
from sim.world.road import RoadMap
from sim.world.vehicle import VehicleMotion

V = 20.0
ROAD = Road(start_heading_deg=0, segments=[{"type": "straight", "length_m": 3000}],
            tunnels=[{"id": "T1", "start_s": 500, "end_s": 2500}])
CFG = Beacons(enabled=True, spacing_m=400, tx_power_dbm=-59, path_loss_exp=2.2)


def _motion():
    t = np.arange(3000 / V * 50) / 50
    z = np.zeros_like(t)
    return VehicleMotion(t=t, s=V * t, v=z + V, a=z, yaw=z, yaw_rate=z, pitch=z, a_lat=z, a_vert=z)


def test_rssi_peak_at_passing_time_and_disabled_is_empty(monkeypatch):
    monkeypatch.setattr(ble, "RSSI_STD_DB", 0.0)
    rm, motion = RoadMap(ROAD), _motion()
    out = generate_ble(motion, rm, CFG, np.random.default_rng(0))
    beacons = beacon_positions(rm, CFG)
    assert [b for b, _ in beacons] == ["T1-B1", "T1-B2", "T1-B3", "T1-B4"]
    assert np.all(np.diff(out["t"]) >= 0)
    for bid, s_b in beacons:
        m = out["beacon_id"] == bid
        assert abs(out["t"][m][np.argmax(out["rssi"][m])] - s_b / V) <= 0.1
    off = generate_ble(motion, rm, CFG.model_copy(update={"enabled": False}), np.random.default_rng(0))
    assert all(len(v) == 0 for v in off.values())
