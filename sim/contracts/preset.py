"""Sensor preset models (presets/*.json, see presets/README.md)."""
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Param(_Model):
    value: float
    unit: str = Field(min_length=1)
    source: str = Field(min_length=1)


class ImuAxis(_Model):
    noise_density: Param
    initial_bias_max: Param
    bias_random_walk: Param
    scale_error_max: Param


class Baro(_Model):
    noise_std: Param
    drift_random_walk: Param


class GnssPreset(_Model):
    position_std: Param
    position_corr_time: Param
    speed_std: Param


class Mag(_Model):
    noise_std: Param


class Preset(_Model):
    id: str
    name: str = ""  # display name for the UI; empty = show the id
    description: str
    accel: ImuAxis
    gyro: ImuAxis
    baro: Baro
    gnss: GnssPreset
    mag: Mag


PRESET_DIR = Path(__file__).resolve().parents[2] / "presets"


def load_preset(name: str) -> Preset:
    return Preset.model_validate(json.loads((PRESET_DIR / f"{name}.json").read_text(encoding="utf-8")))
