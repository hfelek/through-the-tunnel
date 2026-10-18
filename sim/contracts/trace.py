"""Trace models (docs/CONTRACTS.md section 3.3). Columnar: one list per field."""
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MapColumns(_Model):
    s: list[float] = []
    x: list[float] = []
    y: list[float] = []
    z: list[float] = []
    heading: list[float] = []
    curvature: list[float] = []
    grade: list[float] = []
    tunnels: list[dict[str, Any]] = []
    exits: list[dict[str, Any]] = []
    speed_limits: list[dict[str, Any]] = []


class Truth(_Model):
    t: list[float] = []
    s: list[float] = []
    v: list[float] = []
    a: list[float] = []
    x: list[float] = []
    y: list[float] = []
    z: list[float] = []
    yaw: list[float] = []
    pitch: list[float] = []


class Imu(_Model):
    t: list[float] = []
    ax: list[float] = []
    ay: list[float] = []
    az: list[float] = []
    gx: list[float] = []
    gy: list[float] = []
    gz: list[float] = []


class Gnss(_Model):
    t: list[float] = []
    x: list[float] = []
    y: list[float] = []
    z: list[float] = []
    speed: list[float] = []
    course: list[float] = []
    h_acc: list[float] = []
    speed_acc: list[float] = []


class Baro(_Model):
    t: list[float] = []
    p_hpa: list[float] = []


class Mag(_Model):
    t: list[float] = []
    mx: list[float] = []
    my: list[float] = []
    mz: list[float] = []


class Ble(_Model):
    t: list[float] = []
    beacon_id: list[str] = []
    rssi: list[float] = []


class Measurements(_Model):
    imu: Imu | None = None
    gnss: Gnss | None = None
    baro: Baro | None = None
    mag: Mag | None = None
    ble: Ble | None = None


class Event(_Model):
    t: float
    type: str
    ref: str | None = None


class EstimateColumns(_Model):
    t: list[float] = []
    s: list[float] = []
    v: list[float] = []
    sigma_s: list[float] = []
    display_s: list[float] = []
    mode: list[str] = []


class Callout(_Model):
    exit: str
    distance_m: float
    t: float
    t_ideal: float


class VehicleTrace(_Model):
    id: str
    truth: Truth | None = None
    measurements: Measurements = Field(default_factory=Measurements)
    events: list[Event] = []
    estimates: dict[str, EstimateColumns] = {}
    callouts: dict[str, list[Callout]] = {}
    metrics: dict[str, dict[str, Any]] = {}


class Trace(_Model):
    schema_version: str = "1.0"
    source: str = "sim"
    scenario_id: str = ""
    map: MapColumns = Field(default_factory=MapColumns)
    vehicles: list[VehicleTrace] = []


def write_trace(trace: Trace, path: str | Path) -> None:
    """Write trace JSON; absent sensors and null fields are omitted."""
    Path(path).write_text(trace.model_dump_json(exclude_none=True))


def read_trace(path: str | Path) -> Trace:
    return Trace.model_validate_json(Path(path).read_text())


def _decimate_columns(block: BaseModel, hz: float) -> BaseModel:
    """Keep the first row, then the next row at least 1/hz after the last kept one."""
    t = block.t  # type: ignore[attr-defined]
    keep: list[int] = []
    last = None
    for i, ti in enumerate(t):
        if last is None or ti - last >= 1.0 / hz - 1e-9:
            keep.append(i)
            last = ti
    data = {name: [col[i] for i in keep] for name, col in block}
    return type(block)(**data)


def decimate(trace: Trace, hz: float) -> Trace:
    """Return a copy with IMU, baro and mag reduced to at most `hz`; everything else untouched."""
    out = trace.model_copy(deep=True)
    for veh in out.vehicles:
        m = veh.measurements
        for name in ("imu", "baro", "mag"):
            block = getattr(m, name)
            if block is not None:
                setattr(m, name, _decimate_columns(block, hz))
    return out
