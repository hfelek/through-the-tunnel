"""Smartphone IMU model (PLAN T3.2): specific force and angular rate in the phone frame."""
import numpy as np

from sim.contracts.preset import ImuAxis, Preset
from sim.contracts.scenario import HandlingEvent, Mount
from sim.world.vehicle import VehicleMotion

G = 9.80665  # standard gravity, m/s^2
# A17 vibration and handling (RMS per axis)
IDLE_ACCEL_RMS, ACCEL_RMS_PER_MPS = 0.03, 0.01  # m/s^2, m/s^2 per m/s
IDLE_GYRO_RMS, GYRO_RMS_PER_MPS = 0.002, 0.0005  # rad/s, rad/s per m/s
HANDLING_ACCEL_RMS, HANDLING_GYRO_RMS = 2.0, 1.0  # m/s^2, rad/s
HANDLING_RAMP_S = 0.5  # mount angles blend to/from new_mount over at most this time

# Vehicle (x fwd, y left, z up) -> flat phone frame (x right, y forward, z up), CONTRACTS 3.1 Mount
_VEHICLE_TO_FLAT = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])


def _rot(axis: str, a: np.ndarray) -> np.ndarray:
    """Rotation matrices (N, 3, 3) about x, y or z by angles a (rad)."""
    c, s, o, z = np.cos(a), np.sin(a), np.ones_like(a), np.zeros_like(a)
    rows = {
        "x": [o, z, z, z, c, -s, z, s, c],
        "y": [c, z, s, z, o, z, -s, z, c],
        "z": [c, -s, z, s, c, z, z, z, o],
    }[axis]
    return np.stack(rows, axis=1).reshape(-1, 3, 3)


def _event_weights(t: np.ndarray, ev: HandlingEvent) -> tuple[np.ndarray, np.ndarray]:
    """(mount blend weight 0..1, event-active mask) over time."""
    ramp = min(HANDLING_RAMP_S, ev.duration_s / 4)
    x = np.minimum((t - ev.t) / ramp, (ev.t + ev.duration_s - t) / ramp)
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x), (t >= ev.t) & (t <= ev.t + ev.duration_s)


def mount_rotations(t: np.ndarray, mount: Mount, events: list[HandlingEvent]) -> tuple[np.ndarray, np.ndarray]:
    """Phone-to-flat rotation per sample (N, 3, 3) and the handling mask (N,)."""
    ang = np.tile([mount.yaw_deg, mount.pitch_deg, mount.roll_deg], (len(t), 1))
    handling = np.zeros(len(t), dtype=bool)
    for ev in events:
        w, active = _event_weights(t, ev)
        new = np.array([ev.new_mount.yaw_deg, ev.new_mount.pitch_deg, ev.new_mount.roll_deg])
        ang = ang + w[:, None] * (new - ang)
        handling |= active
    yaw, pitch, roll = np.radians(ang).T
    return _rot("z", yaw) @ _rot("x", pitch) @ _rot("y", roll), handling  # intrinsic yaw, pitch, roll


def _vehicle_signals(m: VehicleMotion) -> tuple[np.ndarray, np.ndarray]:
    """Specific force and angular rate in the vehicle frame, both (N, 3)."""
    sp, cp = np.sin(m.pitch), np.cos(m.pitch)
    pitch_rate = np.gradient(m.pitch, m.t) if len(m.t) > 1 else np.zeros_like(m.pitch)
    force = np.stack([m.a + G * sp, m.a_lat, m.a_vert + G * cp], axis=1)
    rate = np.stack([m.yaw_rate * sp, -pitch_rate, m.yaw_rate * cp], axis=1)
    return force, rate


def _to_phone(vec: np.ndarray, rot: np.ndarray) -> np.ndarray:
    return np.einsum("nji,nj->ni", rot, vec @ _VEHICLE_TO_FLAT.T)


def _errors(spec: ImuAxis, n: int, dt: float, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per-run scale factor (3,), bias including random walk (N, 3) and white noise (N, 3)."""
    scale = 1.0 + rng.uniform(-1, 1, 3) * spec.scale_error_max.value
    bias = rng.uniform(-1, 1, 3) * spec.initial_bias_max.value
    walk = np.cumsum(rng.normal(0.0, spec.bias_random_walk.value * np.sqrt(dt), (n, 3)), axis=0)
    white = rng.normal(0.0, spec.noise_density.value / np.sqrt(dt), (n, 3))  # sample std = density * sqrt(fs)
    return scale, bias + walk, white


def generate_imu(
    motion: VehicleMotion, mount: Mount, handling_events: list[HandlingEvent], preset: Preset,
    rng: np.random.Generator, noise_free: bool = False,
) -> dict[str, np.ndarray]:
    """IMU columns (t, ax..az, gx..gz) at the motion's sample rate; `noise_free` keeps only the mount transform."""
    n, t = len(motion.t), motion.t
    dt = float(t[1] - t[0]) if n > 1 else 0.01
    rot, handling = mount_rotations(t, mount, handling_events)
    force, rate = _vehicle_signals(motion)
    out = []
    for sig, spec, vib0, vib_k, hand in (
        (force, preset.accel, IDLE_ACCEL_RMS, ACCEL_RMS_PER_MPS, HANDLING_ACCEL_RMS),
        (rate, preset.gyro, IDLE_GYRO_RMS, GYRO_RMS_PER_MPS, HANDLING_GYRO_RMS),
    ):
        x = _to_phone(sig, rot)
        if not noise_free:
            scale, bias, white = _errors(spec, n, dt, rng)
            vib = (vib0 + vib_k * motion.v)[:, None] * rng.normal(size=(n, 3))
            shake = hand * handling[:, None] * rng.normal(size=(n, 3))
            x = x * scale + bias + white + vib + shake
        out.append(x)
    cols = {"t": t}
    for name, v in zip(("ax", "ay", "az"), out[0].T):
        cols[name] = v
    for name, v in zip(("gx", "gy", "gz"), out[1].T):
        cols[name] = v
    return cols


def imu_to_vehicle_accel(
    imu: dict[str, np.ndarray], motion: VehicleMotion, mount: Mount, handling_events: list[HandlingEvent]
) -> np.ndarray:
    """Inverse transform (N, 3): kinematic vehicle-frame acceleration from phone accelerometer samples."""
    rot, _ = mount_rotations(motion.t, mount, handling_events)
    flat = np.einsum("nij,nj->ni", rot, np.stack([imu["ax"], imu["ay"], imu["az"]], axis=1))
    force = flat @ _VEHICLE_TO_FLAT  # transpose of the orthogonal vehicle->flat map
    up = np.stack([np.sin(motion.pitch), np.zeros_like(motion.pitch), np.cos(motion.pitch)], axis=1)
    return force - G * up
