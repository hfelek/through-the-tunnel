import numpy as np

from sim.contracts.preset import load_preset
from sim.contracts.scenario import Mount, Road, TunnelEnv
from sim.sensors.imu import _VEHICLE_TO_FLAT, _to_phone, mount_rotations
from sim.sensors.mag import B_WORLD_UT, generate_mag
from sim.world.road import RoadMap
from sim.world.vehicle import VehicleMotion

V = 20.0
AZ_B = np.arctan2(B_WORLD_UT[1], B_WORLD_UT[0])  # world azimuth of the horizontal field, CCW from east
ENV = TunnelEnv(pressure_step_pa=20, fan_pressure_noise_pa=8, mag_disturbance_ut=25)
MOUNT = Mount(yaw_deg=4, pitch_deg=65, roll_deg=-2)


def _motion(road_map, length_m, rate=50):
    t = np.arange(int(length_m / V * rate)) / rate
    s, z = V * t, np.zeros(int(length_m / V * rate))
    yaw = road_map.at(s)["heading"]
    return VehicleMotion(t=t, s=s, v=z + V, a=z, yaw=yaw, yaw_rate=z, pitch=z + np.arctan(0.04), a_lat=z, a_vert=z)


def mag_yaw(mag, motion, mount, events=()):
    """Yaw from the magnetometer, tilt-compensated with the true gravity direction in the phone frame."""
    rot, _ = mount_rotations(motion.t, mount, list(events))
    up_v = np.stack([np.sin(motion.pitch), np.zeros_like(motion.t), np.cos(motion.pitch)], axis=1)
    g_phone = _to_phone(up_v, rot)  # same helper the IMU uses
    to_vehicle = lambda p: np.einsum("nij,nj->ni", rot, p) @ _VEHICLE_TO_FLAT
    b, u = to_vehicle(np.stack([mag["mx"], mag["my"], mag["mz"]], axis=1)), to_vehicle(g_phone)
    ex = np.array([1.0, 0.0, 0.0]) - u[:, :1] * u  # vehicle forward axis projected on the horizontal plane
    ex /= np.linalg.norm(ex, axis=1, keepdims=True)
    alpha = np.arctan2(np.einsum("ni,ni->n", b, np.cross(u, ex)), np.einsum("ni,ni->n", b, ex))
    return (AZ_B - alpha + np.pi) % (2 * np.pi) - np.pi


def test_noise_free_norm_and_heading_on_a_grade():
    road = Road(start_heading_deg=30, segments=[
        {"type": "straight", "length_m": 500, "grade_pct": 4},
        {"type": "arc", "length_m": 500, "radius_m": 300, "turn": "left", "grade_pct": 4},
    ])
    rm = RoadMap(road)
    motion, preset = _motion(rm, 1000), load_preset("flagship_2024").model_copy(deep=True)
    preset.mag.noise_std.value = 0.0
    mag = generate_mag(motion, rm, ENV, preset, MOUNT, [], 50.0, np.random.default_rng(0))
    norm = np.linalg.norm(np.stack([mag["mx"], mag["my"], mag["mz"]]), axis=0)
    assert np.all(np.abs(norm - 48.15) < 0.05)
    true_yaw = (np.interp(mag["t"], motion.t, motion.yaw) + np.pi) % (2 * np.pi) - np.pi
    err = (mag_yaw(mag, motion, MOUNT) - true_yaw + np.pi) % (2 * np.pi) - np.pi
    assert np.all(np.abs(np.degrees(err)) < 1.0)


def test_disturbance_is_zero_outside_tunnels():
    road = Road(start_heading_deg=0, segments=[{"type": "straight", "length_m": 1500}],
                tunnels=[{"id": "T1", "start_s": 500, "end_s": 1000}])
    rm = RoadMap(road)
    motion, preset = _motion(rm, 1500), load_preset("flagship_2024").model_copy(deep=True)
    preset.mag.noise_std.value = 0.0
    on, off = (generate_mag(motion, rm, ENV, preset, MOUNT, [], 50.0, np.random.default_rng(0), tunnel_effects=fx) for fx in (True, False))
    s = np.interp(on["t"], motion.t, motion.s)
    outside = ~rm.in_tunnel(s)
    assert (outside & (s > 1000) & (s < 1001)).any() and (outside & (s < 500) & (s > 499)).any()
    for k in ("mx", "my", "mz"):
        assert np.array_equal(on[k][outside], off[k][outside]) and not np.allclose(on[k][~outside], off[k][~outside])
