"""BLE beacon model (PLAN T3.6): iBeacon advertisements received as log-distance path-loss RSSI."""
import numpy as np

from sim.contracts.scenario import Beacons
from sim.world.road import RoadMap
from sim.world.vehicle import VehicleMotion

ADVERT_INTERVAL_S = 0.1  # Apple iBeacon specification: fixed 100 ms advertising interval
LATERAL_M, VERTICAL_M = 2.5, 2.0  # A26
RSSI_STD_DB = 4.0  # A24
DETECTION_DBM = -90.0  # A25


def beacon_positions(road_map: RoadMap, cfg: Beacons) -> list[tuple[str, float]]:
    """Map knowledge: (beacon id, s) for beacons inside tunnels at start_s + k * spacing_m, k = 1, 2, ... while s < end_s."""
    out = []
    for tun in road_map.tunnels:
        k = 1
        while tun.start_s + k * cfg.spacing_m < tun.end_s:
            out.append((f"{tun.id}-B{k}", tun.start_s + k * cfg.spacing_m))
            k += 1
    return out


def generate_ble(motion: VehicleMotion, road_map: RoadMap, cfg: Beacons, rng: np.random.Generator) -> dict[str, np.ndarray]:
    """BLE columns (t, beacon_id, rssi), sorted by t then beacon_id; only packets at or above the detection threshold."""
    beacons = sorted(beacon_positions(road_map, cfg)) if cfg.enabled else []
    if not beacons:
        return {"t": np.empty(0), "beacon_id": np.empty(0, dtype=str), "rssi": np.empty(0)}
    t = motion.t[0] + ADVERT_INTERVAL_S * np.arange(int(np.floor((motion.t[-1] - motion.t[0]) / ADVERT_INTERVAL_S + 1e-9)) + 1)
    s = np.interp(t, motion.t, motion.s)
    noise = rng.normal(0.0, RSSI_STD_DB, (len(t), len(beacons)))  # one independent draw per packet
    ds = s[:, None] - np.array([b[1] for b in beacons])[None, :]
    d = np.sqrt(ds**2 + LATERAL_M**2 + VERTICAL_M**2)
    rssi = cfg.tx_power_dbm - 10.0 * cfg.path_loss_exp * np.log10(d) + noise  # tx_power_dbm = RSSI at 1 m
    i, j = np.nonzero(rssi >= DETECTION_DBM)  # row-major: by time, then beacon id
    ids = np.array([b[0] for b in beacons])
    return {"t": t[i], "beacon_id": ids[j], "rssi": rssi[i, j]}
