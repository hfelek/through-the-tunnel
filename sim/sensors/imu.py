"""Smartphone IMU model (PLAN T3.2): specific force and angular rate in the phone frame."""
import numpy as np

from sim.contracts.preset import ImuAxis, Preset
from sim.contracts.scenario import HandlingEvent, Mount
from sim.world.vehicle import VehicleMotion

G = 9.80665  # standard gravity, m/s^2
# A17 vibration and handling (RMS per axis)
IDLE_ACCEL_RMS, ACCEL_RMS_PER_MPS = 0.03, 0.01  # m/s^2, m/s^2 per m/s
IDLE_GYRO_RMS, GYRO_RMS_PER_MPS = 0.002, 0.0005  # rad/s, rad/s per m/s
HANDLING_ACCEL_RMS = 2.0  # m/s^2, hand translation while the phone is picked up
# A17 handling as an orientation path (rotation-vector std per axis, deg)
PICKUP_STD_DEG, REORIENT_STD_DEG, WOBBLE_STD_DEG = 15.0, 20.0, 5.0
MOVE_S = 1.0  # pick-up, put-back and re-orientation moves take at most this long (T/4 for very short events)
REORIENT_EVERY_S = (10.0, 30.0)  # while held, a new hand orientation at uniform intervals; only if the hold exceeds 10 s
WOBBLE_HZ = (0.5, 2.0)

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


def _skew(v: np.ndarray) -> np.ndarray:
    z = np.zeros(v.shape[:-1])
    return np.stack([z, -v[..., 2], v[..., 1], v[..., 2], z, -v[..., 0], -v[..., 1], v[..., 0], z], axis=-1).reshape(*v.shape[:-1], 3, 3)


def _exp(v: np.ndarray) -> np.ndarray:
    """Rotation vectors (..., 3) -> rotation matrices (..., 3, 3) (Rodrigues)."""
    th2 = np.sum(v * v, axis=-1)
    th = np.sqrt(th2)
    small = th < 1e-6
    safe = np.where(small, 1.0, th)
    a = np.where(small, 1.0 - th2 / 6.0, np.sin(safe) / safe)
    b = np.where(small, 0.5 - th2 / 24.0, (1.0 - np.cos(safe)) / safe**2)
    k = _skew(v)
    return np.eye(3) + a[..., None, None] * k + b[..., None, None] * (k @ k)


def _log(r: np.ndarray) -> np.ndarray:
    """Rotation matrices (..., 3, 3) -> rotation vectors (..., 3); valid away from 180 deg."""
    vee = 0.5 * np.stack([r[..., 2, 1] - r[..., 1, 2], r[..., 0, 2] - r[..., 2, 0], r[..., 1, 0] - r[..., 0, 1]], axis=-1)
    s = np.linalg.norm(vee, axis=-1)
    th = np.arctan2(s, 0.5 * (np.trace(r, axis1=-2, axis2=-1) - 1.0))
    return vee * np.where(s < 1e-12, 1.0, th / np.where(s < 1e-12, 1.0, s))[..., None]


def _smooth(x: np.ndarray) -> np.ndarray:
    """Smooth step 0..1 with zero slope at both ends."""
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def _mount_matrix(m: Mount) -> np.ndarray:
    yaw, pitch, roll = np.radians([[m.yaw_deg], [m.pitch_deg], [m.roll_deg]])
    return (_rot("z", yaw) @ _rot("x", pitch) @ _rot("y", roll))[0]  # intrinsic yaw, pitch, roll


class _EventPath:
    """Phone-to-flat orientation during one handling event (A17): pick-up, hold with re-orientations, put-back, wobble."""

    def __init__(self, ev: HandlingEvent, r_old: np.ndarray, rng: np.random.Generator) -> None:
        self.t0, self.dur = ev.t, ev.duration_s
        self.move = min(MOVE_S, self.dur / 4)
        self.r_new = _mount_matrix(ev.new_mount)
        std = np.radians
        r_hand = r_old @ _exp(rng.normal(0.0, std(PICKUP_STD_DEG), 3))
        u, self.freq = rng.normal(size=(3, 3)), rng.uniform(*WOBBLE_HZ, (3, 3))
        self.phase = rng.uniform(0.0, 2 * np.pi, (3, 3))
        # three sinusoids per axis whose summed variance is the wobble std
        self.amp = u / np.linalg.norm(u, axis=1, keepdims=True) * std(WOBBLE_STD_DEG) * np.sqrt(2.0)
        starts, r_from, r_to = [0.0], [r_old], [r_hand]
        hold_end = self.dur - self.move
        if hold_end - self.move > REORIENT_EVERY_S[0]:
            s = self.move + rng.uniform(*REORIENT_EVERY_S)
            while s + self.move <= hold_end:
                starts.append(s)
                r_from.append(r_to[-1])
                r_to.append(r_to[-1] @ _exp(rng.normal(0.0, std(REORIENT_STD_DEG), 3)))
                s += rng.uniform(*REORIENT_EVERY_S)
        starts.append(hold_end)  # put-back from the current hand orientation
        r_from.append(r_to[-1])
        r_to.append(self.r_new)
        self.starts = np.array(starts)
        self.r_from = np.stack(r_from)
        self.delta = _log(np.swapaxes(self.r_from, 1, 2) @ np.stack(r_to))

    def rotations(self, t: np.ndarray) -> np.ndarray:
        tau = t - self.t0
        k = np.searchsorted(self.starts, tau, side="right") - 1
        sigma = _smooth((tau - self.starts[k]) / self.move)
        main = self.r_from[k] @ _exp(sigma[:, None] * self.delta[k])
        win = _smooth(tau / (self.move / 2)) * _smooth((self.dur - tau) / (self.move / 2))
        wobble = np.sum(self.amp * np.sin(2 * np.pi * self.freq * tau[:, None, None] + self.phase), axis=2)
        return main @ _exp(win[:, None] * wobble)


class MountPath:
    """Phone-to-flat rotation over time: the mount, plus a physically continuous path for every handling event.

    Built once per vehicle (the random draws happen here) and shared by the IMU and the magnetometer.
    """

    def __init__(self, mount: Mount, events: list[HandlingEvent], rng: np.random.Generator) -> None:
        self.base = _mount_matrix(mount)
        self.events: list[_EventPath] = []
        r_old = self.base
        for ev in sorted(events, key=lambda e: e.t):
            self.events.append(_EventPath(ev, r_old, rng))
            r_old = self.events[-1].r_new

    def rotations(self, t: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Rotation per sample (N, 3, 3) and the handling mask (N,)."""
        rot = np.tile(self.base, (len(t), 1, 1))
        handling = np.zeros(len(t), dtype=bool)
        for e in self.events:
            rot[t > e.t0 + e.dur] = e.r_new
            inside = (t >= e.t0) & (t <= e.t0 + e.dur)
            rot[inside] = e.rotations(t[inside])
            handling |= inside
        return rot, handling


def mount_rate(rot: np.ndarray, handling: np.ndarray, dt: float) -> np.ndarray:
    """Angular rate of the mount path in the phone frame (N, 3): log(R_i^T R_(i+1)) / dt; exactly zero off-event."""
    rate = np.zeros((len(rot), 3))
    step = handling[:-1] | handling[1:]
    if step.any():
        i = np.flatnonzero(step)
        rate[i] = _log(np.swapaxes(rot[i], 1, 2) @ rot[i + 1]) / dt
        rate[-1] = rate[-2]
    return rate


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
    rng: np.random.Generator, noise_free: bool = False, path: MountPath | None = None,
) -> dict[str, np.ndarray]:
    """IMU columns (t, ax..az, gx..gz) at the motion's sample rate; `noise_free` keeps only the mount transform."""
    n, t = len(motion.t), motion.t
    dt = float(t[1] - t[0]) if n > 1 else 0.01
    path = path or MountPath(mount, handling_events, rng)
    rot, handling = path.rotations(t)
    force, rate = _vehicle_signals(motion)
    # the phone's rotation rate is the vehicle's, seen from the phone, plus the mount path's own
    signals = (_to_phone(force, rot), _to_phone(rate, rot) + mount_rate(rot, handling, dt))
    out = []
    for x, spec, vib0, vib_k, hand in (
        (signals[0], preset.accel, IDLE_ACCEL_RMS, ACCEL_RMS_PER_MPS, HANDLING_ACCEL_RMS),
        (signals[1], preset.gyro, IDLE_GYRO_RMS, GYRO_RMS_PER_MPS, 0.0),  # hand rotation is in the path, not noise
    ):
        if not noise_free:
            scale, bias, white = _errors(spec, n, dt, rng)
            vib = (vib0 + vib_k * motion.v)[:, None] * rng.normal(size=(n, 3))
            x = x * scale + bias + white + vib
            if hand:
                x = x + hand * handling[:, None] * rng.normal(size=(n, 3))
        out.append(x)
    cols = {"t": t}
    for name, v in zip(("ax", "ay", "az"), out[0].T):
        cols[name] = v
    for name, v in zip(("gx", "gy", "gz"), out[1].T):
        cols[name] = v
    return cols


def imu_to_vehicle_accel(imu: dict[str, np.ndarray], motion: VehicleMotion, path: MountPath) -> np.ndarray:
    """Inverse transform (N, 3): kinematic vehicle-frame acceleration from phone accelerometer samples."""
    rot, _ = path.rotations(motion.t)
    flat = np.einsum("nij,nj->ni", rot, np.stack([imu["ax"], imu["ay"], imu["az"]], axis=1))
    force = flat @ _VEHICLE_TO_FLAT  # transpose of the orthogonal vehicle->flat map
    up = np.stack([np.sin(motion.pitch), np.zeros_like(motion.pitch), np.cos(motion.pitch)], axis=1)
    return force - G * up
