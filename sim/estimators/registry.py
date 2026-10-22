"""Estimator registry: the API and UI list methods from here."""
from __future__ import annotations

from typing import Any, TypeVar

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


class EstimatorFailed(Exception):
    """An estimator raised while running; carries its id so the API can name it."""


def _defaults(cls: type) -> dict[str, Any]:
    return dict(getattr(cls, "default_params", {}))


def _param_info(cls: type) -> dict[str, dict[str, str]]:
    return {k: dict(v) for k, v in getattr(cls, "param_info", {}).items()}


def _constraints(cls: type) -> dict[str, dict[str, Any]]:
    return {k: dict(v) for k, v in getattr(cls, "constraints", {}).items()}


def list_estimators() -> list[dict[str, Any]]:
    """Registry entries with default parameters, display info and constraints (`type` int / float / bool, optional `min` / `gt`)."""
    return [
        {"id": k, "label": c.label, "params": _defaults(c), "param_info": _param_info(c), "constraints": _constraints(c)}
        for k, c in _REGISTRY.items()
    ]


def validate_params(key: str, params: dict[str, Any]) -> None:
    """Raise ValueError naming the parameter if a name is unknown or a value is outside its constraints."""
    cls = _REGISTRY[key]
    defaults, cons = _defaults(cls), _constraints(cls)
    for name, value in params.items():
        if name not in defaults:
            raise ValueError(f"estimator {key!r}: unknown parameter {name!r} (known: {sorted(defaults)})")
        c = cons.get(name, {})
        if c.get("type") == "bool":  # on/off switch (no estimator has one since T8.4-CR2)
            if not isinstance(value, bool):
                raise TypeError(f"estimator {key!r}: parameter {name!r} must be true or false, got {value!r}")
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"estimator {key!r}: parameter {name!r} must be a number, got {value!r}")
        if c.get("type") == "int" and value != int(value):
            raise ValueError(f"estimator {key!r}: parameter {name!r} must be an integer, got {value}")
        if "min" in c and value < c["min"]:
            raise ValueError(f"estimator {key!r}: parameter {name!r} must be >= {c['min']}, got {value}")
        if "gt" in c and value <= c["gt"]:
            raise ValueError(f"estimator {key!r}: parameter {name!r} must be > {c['gt']}, got {value}")


def get_estimator(key: str) -> type[Estimator]:
    return _REGISTRY[key]
