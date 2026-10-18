"""Estimator-facing types (CONTRACTS 3.4): plain dataclasses, no validation overhead."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, Protocol

if TYPE_CHECKING:
    from sim.world.road import RoadMap  # T2.1

Kind = Literal["imu", "gnss", "baro", "mag", "ble"]
Mode = Literal["gnss", "dead_reckoning", "recovering"]


@dataclass(slots=True)
class Measurement:
    """One sensor sample; `data` keys are the trace column names (ax, p_hpa, ...)."""

    t: float
    kind: Kind
    data: dict[str, Any]


@dataclass(slots=True)
class Estimate:
    t: float
    s: float
    v: float
    sigma_s: float
    sigma_v: float
    mode: Mode
    extras: dict[str, Any] = field(default_factory=dict)


class Estimator(Protocol):
    id: str
    label: str

    def reset(self, road: RoadMap, params: dict) -> None: ...
    def update(self, m: Measurement) -> None: ...
    def estimate(self, t: float) -> Estimate: ...
