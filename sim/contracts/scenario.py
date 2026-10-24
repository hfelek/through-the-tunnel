"""Scenario models (docs/CONTRACTS.md section 3.2)."""
import json
import math
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sim.world.speed_change import COMFORT_ACCEL_MPS2, s_curve_distance


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


Range = tuple[float, float]


def _check_range(name: str, r: Range) -> None:
    if r[0] > r[1]:
        raise ValueError(f"{name} must be [min, max] with min <= max, got {list(r)}")


class RatesHz(_Model):
    imu: float = Field(gt=0)
    gnss: float = Field(gt=0)
    baro: float = Field(gt=0)
    mag: float = Field(gt=0)
    output: float = Field(gt=0)


class Straight(_Model):
    type: Literal["straight"]
    length_m: float = Field(gt=0)
    grade_pct: float = 0


class Arc(_Model):
    type: Literal["arc"]
    length_m: float = Field(gt=0)
    radius_m: float = Field(gt=0)
    turn: Literal["left", "right"]
    grade_pct: float = 0


Segment = Annotated[Straight | Arc, Field(discriminator="type")]


class Tunnel(_Model):
    id: str
    start_s: float
    end_s: float


class Exit(_Model):
    id: str
    s: float
    name: str = ""


class SpeedLimit(_Model):
    from_s: float
    to_s: float
    kmh: float = Field(gt=0)


class Road(_Model):
    start_heading_deg: float
    segments: list[Segment] = Field(min_length=1)
    tunnels: list[Tunnel] = []
    exits: list[Exit] = []
    speed_limits: list[SpeedLimit] = []

    @property
    def length_m(self) -> float:
        return sum(seg.length_m for seg in self.segments)

    @model_validator(mode="after")
    def _on_road(self) -> "Road":
        length = self.length_m
        for t in self.tunnels:
            if not 0 <= t.start_s < t.end_s <= length:
                raise ValueError(
                    f"tunnel '{t.id}' spans {t.start_s}-{t.end_s} m but the road is "
                    f"{length} m long (need 0 <= start_s < end_s <= road length)"
                )
        for e in self.exits:
            if not 0 <= e.s <= length:
                raise ValueError(f"exit '{e.id}' at s={e.s} m is off the road (length {length} m)")
        for sl in self.speed_limits:
            if not 0 <= sl.from_s < sl.to_s <= length:
                raise ValueError(f"speed limit {sl.from_s}-{sl.to_s} m is off the road ({length} m)")
        return self


class SpeedPoint(_Model):
    type: Literal["speed"]
    s: float
    kmh: float = Field(gt=0)
    rate_mps2: float = Field(default=1.5, gt=0)  # A11


class StopPoint(_Model):
    type: Literal["stop"]
    s: float
    dwell_s: float = Field(ge=0)
    decel_mps2: float = Field(default=1.5, gt=0)  # A11
    accel_mps2: float = Field(default=1.5, gt=0)  # A11


class TrafficSection(_Model):
    type: Literal["traffic"]
    from_s: float
    to_s: float
    kmh: float = Field(gt=0)
    stop_s: Range
    go_s: Range

    @model_validator(mode="after")
    def _ranges(self) -> "TrafficSection":
        if not self.from_s < self.to_s:
            raise ValueError(f"traffic needs from_s < to_s, got {self.from_s} and {self.to_s}")
        _check_range("traffic stop_s", self.stop_s)
        _check_range("traffic go_s", self.go_s)
        return self


PlanPoint = Annotated[SpeedPoint | StopPoint | TrafficSection, Field(discriminator="type")]


class Mount(_Model):
    yaw_deg: float = 0
    pitch_deg: float = 0
    roll_deg: float = 0


class HandlingEvent(_Model):
    t: float = Field(ge=0)
    duration_s: float = Field(gt=0)
    new_mount: Mount


class Phone(_Model):
    preset: str
    mount: Mount
    handling_events: list[HandlingEvent] = []


class Vehicle(_Model):
    id: str
    start_s: float
    start_t: float = 0
    initial_kmh: float = Field(ge=0)
    speed_jitter_kmh: float = Field(default=0, ge=0)
    plan: list[PlanPoint]
    phone: Phone


class GnssEnv(_Model):
    portal_degrade_m: float = Field(ge=0)
    reacquire_delay_s: Range
    bad_fixes_after_exit: int = Field(ge=0)
    bad_fix_error_m: float = Field(ge=0)

    @model_validator(mode="after")
    def _ranges(self) -> "GnssEnv":
        _check_range("reacquire_delay_s", self.reacquire_delay_s)
        return self


class TunnelEnv(_Model):
    pressure_step_pa: float
    fan_pressure_noise_pa: float = Field(ge=0)
    mag_disturbance_ut: float = Field(ge=0)


class Beacons(_Model):
    enabled: bool
    spacing_m: float = Field(gt=0)
    tx_power_dbm: float
    path_loss_exp: float = Field(gt=0)


def _point_s(p: PlanPoint) -> float:
    return p.from_s if isinstance(p, TrafficSection) else p.s


def _check_plan(v: Vehicle, length: float) -> None:
    """Plan points are sorted, on the road, and every slowdown/stop leaves room to brake at its rate."""
    kmh = 1 / 3.6
    pos, speed = v.start_s, v.initial_kmh * kmh  # where the car is settled at `speed` after the previous point
    last_s = -math.inf
    prev_s = v.start_s  # position of the previous point (the start for point 1)
    for i, p in enumerate(v.plan, 1):
        name = f"vehicle '{v.id}': plan point {i} ({p.type}"
        s = _point_s(p)
        end = p.to_s if isinstance(p, TrafficSection) else s
        if not (0 <= s and end <= length):
            raise ValueError(f"{name}, s={s} m) is off the road ({length} m)")
        if not s > last_s:
            raise ValueError(f"{name}, s={s} m) must come after the previous point (s={last_s} m): points are sorted by position")
        before, prev_s, last_s = prev_s, end, end
        if isinstance(p, TrafficSection):
            pos = end + s_curve_distance(p.kmh * kmh, speed, COMFORT_ACCEL_MPS2)  # the car returns to the target speed
            continue
        v_new, rate = (0.0, p.decel_mps2) if isinstance(p, StopPoint) else (p.kmh * kmh, p.rate_mps2)
        if v_new < speed:  # a slowdown or stop needs room to brake after the previous point
            need = s_curve_distance(speed, v_new, rate)
            if s - pos < need:
                raise ValueError(
                    f"{name}, s={s} m) is too close to the previous point: braking from {speed / kmh:.0f} to "
                    f"{v_new / kmh:.0f} km/h at {rate} m/s² needs at least {pos + need - before:.0f} m after it (s >= {pos + need:.0f} m)"
                )
        if isinstance(p, StopPoint):
            pos = s + s_curve_distance(0.0, speed, p.accel_mps2)  # the car sets off again after the dwell
        elif v_new < speed:
            pos = s  # the new speed is reached exactly at s
        else:
            pos = s + s_curve_distance(speed, v_new, rate)  # the car accelerates from s on
        speed = v_new if isinstance(p, SpeedPoint) else speed


class Scenario(_Model):
    schema_version: str
    id: str
    title: str = ""  # display name for the UI; empty = show the id
    description: str = ""
    seed: int
    rates_hz: RatesHz
    road: Road
    vehicles: list[Vehicle] = Field(min_length=1)
    gnss_env: GnssEnv
    tunnel_env: TunnelEnv
    beacons: Beacons

    @model_validator(mode="after")
    def _vehicles_on_road(self) -> "Scenario":
        length = self.road.length_m
        for v in self.vehicles:
            if not 0 <= v.start_s <= length:
                raise ValueError(f"vehicle '{v.id}' start_s={v.start_s} m is off the road ({length} m)")
            _check_plan(v, length)
        return self


def load_scenario(path: str | Path) -> Scenario:
    """Read and validate a scenario JSON file."""
    return Scenario.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))
