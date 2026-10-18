"""Scenario models (docs/CONTRACTS.md section 3.2)."""
import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class Cruise(_Model):
    type: Literal["cruise"]
    kmh: float = Field(ge=0)
    until_s: float


class Ramp(_Model):
    type: Literal["ramp"]
    to_kmh: float = Field(ge=0)
    accel_mps2: float = Field(gt=0)


class Stop(_Model):
    type: Literal["stop"]
    at_s: float
    decel_mps2: float = Field(gt=0)
    dwell_s: float = Field(ge=0)


class StopAndGo(_Model):
    type: Literal["stop_and_go"]
    from_s: float
    to_s: float
    kmh: float = Field(gt=0)
    stop_s: Range
    go_s: Range

    @model_validator(mode="after")
    def _ranges(self) -> "StopAndGo":
        if not self.from_s < self.to_s:
            raise ValueError(f"stop_and_go needs from_s < to_s, got {self.from_s} and {self.to_s}")
        _check_range("stop_and_go stop_s", self.stop_s)
        _check_range("stop_and_go go_s", self.go_s)
        return self


ProfileItem = Annotated[Cruise | Ramp | Stop | StopAndGo, Field(discriminator="type")]


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
    profile: list[ProfileItem]
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


class Scenario(_Model):
    schema_version: str
    id: str
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
            for p in v.profile:
                if isinstance(p, Cruise) and not 0 <= p.until_s <= length:
                    raise ValueError(f"vehicle '{v.id}': cruise until_s={p.until_s} m is off the road")
                if isinstance(p, Stop) and not 0 <= p.at_s <= length:
                    raise ValueError(f"vehicle '{v.id}': stop at_s={p.at_s} m is off the road")
                if isinstance(p, StopAndGo) and not (0 <= p.from_s and p.to_s <= length):
                    raise ValueError(f"vehicle '{v.id}': stop_and_go {p.from_s}-{p.to_s} m is off the road")
        return self


def load_scenario(path: str | Path) -> Scenario:
    """Read and validate a scenario JSON file."""
    return Scenario.model_validate(json.loads(Path(path).read_text()))
