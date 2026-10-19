"""Vehicle motion along the road: s(t), v(t), a(t) and body kinematics (PLAN T2.2)."""
import math
from dataclasses import dataclass

import numpy as np

from sim.contracts.scenario import SpeedPoint, StopPoint, TrafficSection, Vehicle
from sim.world.road import RoadMap
from sim.world.speed_change import COMFORT_ACCEL_MPS2, JERK_MPS3, s_curve

KMH = 1 / 3.6
JITTER_FADE_S = 3.0  # jitter fades in/out linearly over this time
JITTER_FREQ_HZ = (0.02, 0.1)  # A27: slow speed variation, 10-50 s periods
VERTICAL_BLEND_M = 40.0  # A12
MIN_GAP_M = 15.0  # A10
GAP_MARGIN_M = 0.01  # numerical margin so discrete steps never dip below the minimum gap
FOLLOW_DECEL_MPS2 = 3.0  # A13
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


class _Run:
    """Steps the vehicle at a fixed dt and records (t, s, v)."""

    def __init__(
        self, vehicle: Vehicle, road_len: float, dt: float, rng: np.random.Generator,
        leader: "VehicleMotion | None" = None, min_gap_m: float = MIN_GAP_M,
    ) -> None:
        self.dt, self.road_len, self.rng = dt, road_len, rng
        self.leader, self.min_gap = leader, min_gap_m
        self.t0, self.s, self.vb = vehicle.start_t, vehicle.start_s, vehicle.initial_kmh * KMH
        self.g = 0.0  # jitter gain 0..1
        n = 4  # A27: sum of 4 random-phase cosines
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
        if self.leader is not None and v > 0:
            v = min(v, self._gap_speed_cap())
        if self.rec:
            self.s += 0.5 * (self.v_prev + v) * self.dt
        self.v_prev = v
        self.rec.append((self.t, self.s, v))
        self.k += 1
        if self.s >= self.road_len:
            raise _RoadEnd
        if self.k * self.dt > MAX_DURATION_S:
            raise ValueError("vehicle never reaches the road end")

    def _gap_speed_cap(self) -> float:
        """Highest speed that still lets the follower stop in time to keep the minimum gap (A10)."""
        lead = self.leader
        s_lead = np.interp(self.t, lead.t, lead.s, right=np.inf)
        room = max(float(s_lead) - self.s - self.min_gap - GAP_MARGIN_M, 0.0)
        if math.isinf(room):
            return math.inf
        v_lead = float(np.interp(self.t, lead.t, lead.v, left=0.0))
        return max(min(v_lead + math.sqrt(2 * FOLLOW_DECEL_MPS2 * max(room - self.v_prev * self.dt, 0.0)), 2 * room / self.dt - self.v_prev), 0.0)

    def change(self, v1: float, accel: float) -> None:
        total, f = s_curve(self.vb, v1, accel)
        for i in range(1, math.ceil(total / self.dt - 1e-9) + 1):
            self.step(f(i * self.dt), False)
        self.vb = v1

    def wait(self, seconds: float) -> None:
        for _ in range(round(seconds / self.dt)):
            self.step(self.vb, False)

    def hold_until(self, s_end: float) -> None:
        """Keep the target speed (with jitter) until the position s_end."""
        while self.s < s_end:
            self.step(self.vb, True)

    def brake_to(self, v1: float, s_end: float, decel: float) -> None:
        """Hold speed, then slow to v1 as late as possible so that v1 is reached exactly at s_end."""
        if self.vb <= v1:
            return
        while True:
            d = s_end - self.s
            total, _ = s_curve(self.vb, v1, decel)
            dist = (self.vb + v1) / 2 * total  # the S-curve is point-symmetric: mean speed (v0+v1)/2
            if d <= dist:
                break
            self.step(self.vb, d > dist + self.vb * JITTER_FADE_S)  # jitter fades out before braking
        self.g = 0.0
        dv = self.vb - v1
        if d > 0:  # brake slightly harder so that the change lands exactly on s_end
            t_need = 2 * d / (self.vb + v1)
            disc = (t_need * JERK_MPS3) ** 2 - 4 * dv * JERK_MPS3  # total = dv/a + a/J  ->  a^2/J - t*a + dv = 0
            decel = math.sqrt(dv * JERK_MPS3) if disc < 0 else (t_need * JERK_MPS3 - math.sqrt(disc)) / 2
        self.change(v1, decel)
        if v1 == 0 and abs(self.s - s_end) < 1.0:  # a stop sits exactly on its point
            self.s = s_end
            self.rec[-1] = (self.rec[-1][0], self.s, 0.0)

    def speed_point(self, p: SpeedPoint, target: float) -> None:
        v1 = p.kmh * KMH
        if v1 < target:
            self.brake_to(v1, p.s, p.rate_mps2)
        else:
            self.hold_until(p.s)
            self.change(v1, p.rate_mps2)

    def stop_point(self, p: StopPoint, target: float) -> None:
        self.brake_to(0.0, p.s, p.decel_mps2)
        self.wait(p.dwell_s)
        self.change(target, p.accel_mps2)

    def traffic(self, p: TrafficSection, target: float) -> None:
        self.hold_until(p.from_s)
        while self.s < p.to_s:
            self.change(p.kmh * KMH, COMFORT_ACCEL_MPS2)
            t_end = self.t + self.rng.uniform(*p.go_s)
            while self.s < p.to_s and self.t < t_end:
                self.step(self.vb, False)
            if self.s >= p.to_s:
                break
            self.change(0.0, COMFORT_ACCEL_MPS2)
            self.wait(self.rng.uniform(*p.stop_s))
        self.change(target, COMFORT_ACCEL_MPS2)


def _road_pitch(road_map: RoadMap) -> tuple[np.ndarray, np.ndarray]:
    """Blended pitch along the road and its derivative d(pitch)/ds."""
    line = road_map.line
    n = int(VERTICAL_BLEND_M / (line.s[1] - line.s[0])) | 1
    pitch = np.convolve(np.pad(np.arctan(line.grade), n // 2, mode="edge"), np.ones(n) / n, mode="valid")
    return pitch, np.gradient(pitch, line.s)


def simulate_vehicle(
    vehicle: Vehicle, road_map: RoadMap, rate_hz: float, rng: np.random.Generator,
    leader: VehicleMotion | None = None, min_gap_m: float = MIN_GAP_M,
) -> VehicleMotion:
    """Run the vehicle's driving plan on the road at `rate_hz` until it reaches the road end.

    With a `leader`, the vehicle slows down so it never gets closer than `min_gap_m` to it.
    """
    run = _Run(vehicle, road_map.length_m, 1.0 / rate_hz, rng, leader, min_gap_m)
    try:
        target = run.vb  # the speed the car returns to after a stop or traffic section
        for p in vehicle.plan:
            if isinstance(p, SpeedPoint):
                run.speed_point(p, target)
                target = p.kmh * KMH
            elif isinstance(p, StopPoint):
                run.stop_point(p, target)
            else:
                run.traffic(p, target)
        while run.vb > 0:  # keep the last target speed to the road end
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


def simulate_vehicles(
    vehicles: list[Vehicle], road_map: RoadMap, rate_hz: float, rng: np.random.Generator, min_gap_m: float = MIN_GAP_M
) -> list[VehicleMotion]:
    """Simulate vehicles in list order; each one follows the previous one in the list (single lane, no overtaking)."""
    motions: list[VehicleMotion] = []
    for vehicle, child in zip(vehicles, rng.spawn(len(vehicles))):
        leader = motions[-1] if motions else None
        if leader is not None:
            s_lead = float(np.interp(vehicle.start_t, leader.t, leader.s, right=np.inf))
            if vehicle.start_s > s_lead - min_gap_m:
                raise ValueError(
                    f"vehicle '{vehicle.id}' starts at s={vehicle.start_s} m at t={vehicle.start_t} s, "
                    f"less than {min_gap_m} m behind its leader '{vehicles[len(motions) - 1].id}' (at s={s_lead:.1f} m)"
                )
        motions.append(simulate_vehicle(vehicle, road_map, rate_hz, child, leader, min_gap_m))
    return motions
