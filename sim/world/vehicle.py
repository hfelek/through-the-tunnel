"""Vehicle motion along the road: s(t), v(t), a(t) and body kinematics (PLAN T2.2)."""
import math
from dataclasses import dataclass

import numpy as np

from sim.contracts.scenario import Cruise, Ramp, Stop, StopAndGo, Vehicle
from sim.world.road import RoadMap

JERK_MPS3 = 2.0  # A11
COMFORT_ACCEL_MPS2 = 1.5  # A11
KMH = 1 / 3.6
JITTER_FADE_S = 3.0  # jitter fades in/out linearly over this time
JITTER_FREQ_HZ = (0.02, 0.1)  # slow speed variation: 10-50 s periods
VERTICAL_BLEND_M = 40.0  # pitch is blended over this length, like road vertical curves
MAX_DURATION_S = 2 * 3600.0


@dataclass
class VehicleMotion:
    """Samples at the IMU rate. `a` is the vehicle-frame longitudinal acceleration (x forward)."""

    t: np.ndarray
    s: np.ndarray
    v: np.ndarray
    a: np.ndarray
    yaw: np.ndarray
    yaw_rate: np.ndarray
    pitch: np.ndarray
    a_lat: np.ndarray  # vehicle y (left), v^2 * curvature
    a_vert: np.ndarray  # vehicle z (up), kinematic part only (no gravity)


class _RoadEnd(Exception):
    pass


def _s_curve(v0: float, v1: float, accel: float) -> tuple[float, "callable"]:
    """Jerk-limited speed change v0 -> v1 with zero acceleration at both ends: (duration, v(tau))."""
    dv = abs(v1 - v0)
    if dv == 0:
        return 0.0, lambda tau: v0
    sign = 1.0 if v1 > v0 else -1.0
    a_pk = min(accel, math.sqrt(dv * JERK_MPS3))
    t1 = a_pk / JERK_MPS3
    t2 = dv / a_pk - t1
    total = 2 * t1 + t2

    def v(tau: float) -> float:
        tau = min(tau, total)
        if tau < t1:
            d = JERK_MPS3 * tau**2 / 2
        elif tau < t1 + t2:
            d = JERK_MPS3 * t1**2 / 2 + a_pk * (tau - t1)
        else:
            d = dv - JERK_MPS3 * (total - tau) ** 2 / 2
        return v0 + sign * d

    return total, v


class _Run:
    """Steps the vehicle at a fixed dt and records (t, s, v)."""

    def __init__(self, vehicle: Vehicle, road_len: float, dt: float, rng: np.random.Generator) -> None:
        self.dt, self.road_len, self.rng = dt, road_len, rng
        self.t0, self.s, self.vb = vehicle.start_t, vehicle.start_s, vehicle.initial_kmh * KMH
        self.g = 0.0  # jitter gain 0..1
        n = 4
        self.f = rng.uniform(*JITTER_FREQ_HZ, n)
        self.phi = rng.uniform(0, 2 * math.pi, n)
        self.amp = vehicle.speed_jitter_kmh * KMH * math.sqrt(2 / n)  # std = speed_jitter_kmh
        self.k = 0
        self.rec: list[tuple[float, float, float]] = []
        self.v_prev = 0.0
        self.step(self.vb, False)

    @property
    def t(self) -> float:
        return self.t0 + self.k * self.dt

    def step(self, vb: float, jitter_on: bool) -> None:
        self.vb = vb
        self.g = min(1.0, self.g + self.dt / JITTER_FADE_S) if jitter_on else max(0.0, self.g - self.dt / JITTER_FADE_S)
        j = self.amp * float(np.sum(np.cos(2 * math.pi * self.f * self.t + self.phi)))
        gain = self.g**2 * (3 - 2 * self.g)  # smoothstep: no acceleration kink at fade ends
        v = max(vb + gain * j, 0.0) if vb > 0 else 0.0
        if self.rec:
            self.s += 0.5 * (self.v_prev + v) * self.dt
        self.v_prev = v
        self.rec.append((self.t, self.s, v))
        self.k += 1
        if self.s >= self.road_len:
            raise _RoadEnd
        if self.k * self.dt > MAX_DURATION_S:
            raise ValueError("vehicle never reaches the road end")

    def change(self, v1: float, accel: float) -> None:
        total, f = _s_curve(self.vb, v1, accel)
        for i in range(1, math.ceil(total / self.dt - 1e-9) + 1):
            self.step(f(i * self.dt), False)
        self.vb = v1

    def wait(self, seconds: float) -> None:
        for _ in range(round(seconds / self.dt)):
            self.step(self.vb, False)

    def cruise(self, item: Cruise) -> None:
        self.change(item.kmh * KMH, COMFORT_ACCEL_MPS2)
        while self.s < item.until_s:
            self.step(self.vb, True)

    def stop(self, item: Stop) -> None:
        a_dec = item.decel_mps2
        while self.vb > 0:
            d = item.at_s - self.s
            total, _ = _s_curve(self.vb, 0.0, a_dec)
            dist = self.vb * total / 2  # the S-curve is point-symmetric: mean speed v0/2
            if d <= dist:
                break
            self.step(self.vb, d > dist + self.vb * JITTER_FADE_S)
        if self.vb > 0:
            self.g = 0.0
            if d > 0:  # brake slightly harder so that the stop lands exactly on at_s
                t_need = 2 * d / self.vb
                disc = (t_need * JERK_MPS3) ** 2 - 4 * self.vb * JERK_MPS3
                a_dec = math.sqrt(self.vb * JERK_MPS3) if disc < 0 else (t_need * JERK_MPS3 - math.sqrt(disc)) / 2
            self.change(0.0, a_dec)
            if abs(self.s - item.at_s) < 1.0:
                self.s = item.at_s
                self.rec[-1] = (self.rec[-1][0], self.s, 0.0)
        self.wait(item.dwell_s)

    def stop_and_go(self, item: StopAndGo) -> None:
        while self.s < item.from_s:
            self.step(self.vb, True)
        while self.s < item.to_s:
            self.change(item.kmh * KMH, COMFORT_ACCEL_MPS2)
            t_end = self.t + self.rng.uniform(*item.go_s)
            while self.s < item.to_s and self.t < t_end:
                self.step(self.vb, False)
            if self.s >= item.to_s:
                break
            self.change(0.0, COMFORT_ACCEL_MPS2)
            self.wait(self.rng.uniform(*item.stop_s))


def _road_pitch(road_map: RoadMap) -> tuple[np.ndarray, np.ndarray]:
    """Blended pitch along the road and its derivative d(pitch)/ds."""
    line = road_map.line
    n = int(VERTICAL_BLEND_M / (line.s[1] - line.s[0])) | 1
    pitch = np.convolve(np.pad(np.arctan(line.grade), n // 2, mode="edge"), np.ones(n) / n, mode="valid")
    return pitch, np.gradient(pitch, line.s)


def simulate_vehicle(vehicle: Vehicle, road_map: RoadMap, rate_hz: float, rng: np.random.Generator) -> VehicleMotion:
    """Run the vehicle's profile on the road at `rate_hz` until it reaches the road end."""
    run = _Run(vehicle, road_map.length_m, 1.0 / rate_hz, rng)
    try:
        for item in vehicle.profile:
            if isinstance(item, Cruise):
                run.cruise(item)
            elif isinstance(item, Ramp):
                run.change(item.to_kmh * KMH, item.accel_mps2)
            elif isinstance(item, Stop):
                run.stop(item)
            elif isinstance(item, StopAndGo):
                run.stop_and_go(item)
        while run.vb > 0:  # keep the last profile speed to the road end
            run.step(run.vb, True)
    except _RoadEnd:
        run.rec[-1] = (run.rec[-1][0], road_map.length_m, run.rec[-1][2])
    t, s, v = (np.array(c) for c in zip(*run.rec))
    pos = road_map.at(s)
    ps, dps = _road_pitch(road_map)
    line_s = road_map.line.s
    return VehicleMotion(
        t=t, s=s, v=v,
        a=np.gradient(v, t) if len(t) > 1 else np.zeros_like(v),
        yaw=pos["heading"],
        yaw_rate=v * pos["curvature"],
        pitch=np.interp(s, line_s, ps),
        a_lat=v**2 * pos["curvature"],
        a_vert=v**2 * np.interp(s, line_s, dps),
    )
