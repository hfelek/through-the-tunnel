"""Estimator registry: the API and UI list methods from here."""
from __future__ import annotations

from typing import TypeVar

from sim.contracts.estimation import Estimator

T = TypeVar("T", bound=type)

_REGISTRY: dict[str, type[Estimator]] = {}


def register(cls: T) -> T:
    """Class decorator: add an estimator class under its `id`."""
    key = cls.id  # type: ignore[attr-defined]
    if key in _REGISTRY:
        raise ValueError(f"estimator id already registered: {key}")
    _REGISTRY[key] = cls  # type: ignore[assignment]
    return cls


def unregister(key: str) -> None:
    _REGISTRY.pop(key, None)


def list_estimators() -> list[dict[str, str]]:
    return [{"id": k, "label": c.label} for k, c in _REGISTRY.items()]


def get_estimator(key: str) -> type[Estimator]:
    return _REGISTRY[key]
