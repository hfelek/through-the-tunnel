"""Smartphone magnetometer model (PLAN T3.5): Earth field in the phone frame plus a tunnel disturbance."""
import numpy as np

from sim.contracts.preset import Preset
from sim.contracts.scenario import HandlingEvent, Mount, TunnelEnv
from sim.sensors.imu import _rot, _to_phone, mount_rotations
from sim.world.road import RESOLUTION_M, RoadMap
from sim.world.vehicle import VehicleMotion

# Istanbul (41.01 N, 28.98 E, sea level, epoch 2026.8), WMM2025 (NOAA NCEI / British Geological Survey):
# total 48.15 uT, declination 6.1 deg east, inclination 59.0 deg down. ENU (east, north, up) in uT; ENU y is treated as true north.
B_WORLD_UT = np.array([2.63, 24.68, -41.26])
CORR_LENGTH_M = 10.0  # A23: spatial correlation length of the tunnel disturbance


def _tunnel_field(road_map: RoadMap, sigma_ut: float, w: np.ndarray) -> np.ndarray:
    """World-frame disturbance on the road's 1 m grid (n, 3): Gauss-Markov inside tunnels, 0 outside and at each start (A23)."""
    phi = np.exp(-RESOLUTION_M / CORR_LENGTH_M)
    d = np.zeros_like(w)
    for tun in road_map.tunnels:
        i0, i1 = int(np.ceil(tun.start_s / RESOLUTION_M)), int(np.floor(tun.end_s / RESOLUTION_M))
        for i in range(i0 + 1, min(i1, len(w) - 1) + 1):
            d[i] = phi * d[i - 1] + sigma_ut * np.sqrt(1.0 - phi**2) * w[i]
    return d


def generate_mag(
    motion: VehicleMotion, road_map: RoadMap, env: TunnelEnv, preset: Preset, mount: Mount,
    handling_events: list[HandlingEvent], rate_hz: float, rng: np.random.Generator, tunnel_effects: bool = True,
) -> dict[str, np.ndarray]:
    """Magnetometer columns (t, mx, my, mz) in uT on a regular grid; white noise is always on."""
    dt = 1.0 / rate_hz
    t = motion.t[0] + dt * np.arange(int(np.floor((motion.t[-1] - motion.t[0]) / dt + 1e-9)) + 1)
    s, yaw, pitch = (np.interp(t, motion.t, a) for a in (motion.s, motion.yaw, motion.pitch))
    # all random draws first, so the stream does not depend on the options
    white = rng.normal(0.0, preset.mag.noise_std.value, (len(t), 3))
    grid_w = rng.normal(size=(int(np.ceil(road_map.length_m / RESOLUTION_M)) + 1, 3))

    b_world = np.tile(B_WORLD_UT, (len(t), 1))
    if tunnel_effects:
        field = _tunnel_field(road_map, env.mag_disturbance_ut, grid_w)
        grid_s = RESOLUTION_M * np.arange(len(field))
        dist = np.stack([np.interp(s, grid_s, field[:, k]) for k in range(3)], axis=1)
        b_world = b_world + dist * road_map.in_tunnel(s)[:, None]  # the 1 m grid interpolation must not leak past a portal
    vehicle_to_world = _rot("z", yaw) @ _rot("y", -pitch)  # forward axis = (cos y cos p, sin y cos p, sin p), roll 0
    b_vehicle = np.einsum("nji,nj->ni", vehicle_to_world, b_world)
    rot, _ = mount_rotations(t, mount, handling_events)
    b_phone = _to_phone(b_vehicle, rot) + white
    return {"t": t, "mx": b_phone[:, 0], "my": b_phone[:, 1], "mz": b_phone[:, 2]}
