import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from sim.contracts.scenario import Scenario, load_scenario

EXAMPLE = Path("scenarios/curved_3km_exit_inside.json")


def _raw() -> dict:
    return copy.deepcopy(json.loads(EXAMPLE.read_text()))


def test_example_validates() -> None:
    sc = load_scenario(EXAMPLE)
    assert sc.road.length_m == 6600
    assert sc.vehicles[0].plan[1].type == "stop"


def test_tunnel_beyond_road_rejected() -> None:
    raw = _raw()
    raw["road"]["tunnels"][0]["end_s"] = 9000
    with pytest.raises(ValidationError, match="tunnel 'T1'.*6600"):
        Scenario.model_validate(raw)


def test_exit_off_road_rejected() -> None:
    raw = _raw()
    raw["road"]["exits"][0]["s"] = 7000
    with pytest.raises(ValidationError, match="exit 'E1'.*off the road"):
        Scenario.model_validate(raw)


def test_unknown_plan_type_rejected() -> None:
    raw = _raw()
    raw["vehicles"][0]["plan"][0]["type"] = "teleport"
    with pytest.raises(ValidationError, match="teleport"):
        Scenario.model_validate(raw)
