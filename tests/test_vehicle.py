from itertools import pairwise

import numpy as np

from sim.contracts.scenario import Road, Vehicle
from sim.world.road import RoadMap
from sim.world.vehicle import simulate_vehicle, simulate_vehicles

ROAD = Road(
    start_heading_deg=0,
    segments=[
        {"type": "straight", "length_m": 1000},
        {"type": "arc", "length_m": 800 * np.pi / 2, "radius_m": 800, "turn": "left"},
    ],
)


def _vehicle(plan, jitter=2.0):
    return Vehicle.model_validate({
        "id": "v", "start_s": 0, "initial_kmh": 72, "speed_jitter_kmh": jitter, "plan": plan,
        "phone": {"preset": "x", "mount": {}},
    })


def _run(plan, seed=1, jitter=2.0):
    return simulate_vehicle(_vehicle(plan, jitter), RoadMap(ROAD), 100.0, np.random.default_rng(seed))


STOP = [{"type": "stop", "s": 600, "dwell_s": 5, "decel_mps2": 2.0}]


def test_stop_exact_and_nonnegative():
    m = _run(STOP)
    i = np.flatnonzero(m.v == 0)
    assert m.v.min() >= 0 and abs(m.s[i[0]] - 600) < 1e-6
    assert abs((m.t[i[-1]] - m.t[i[0]]) - 5) < 0.02 and m.s[-1] == ROAD.length_m


def test_same_seed_same_result():
    assert np.array_equal(_run(STOP, 3).v, _run(STOP, 3).v)
    assert not np.array_equal(_run(STOP, 3).v, _run(STOP, 4).v)


def test_lateral_acceleration_in_curve():
    m = _run([])
    k = (m.s > 1100) & (m.s < 2000)
    assert np.allclose(m.a_lat[k], m.v[k] ** 2 / 800)


def test_three_vehicles_keep_minimum_gap():
    slow = [{"type": "stop", "s": 1000, "dwell_s": 5, "decel_mps2": 2.0}]
    fast = []
    vs = [{"id": f"v{i}", "start_s": s0, "initial_kmh": kmh, "speed_jitter_kmh": 1.0, "plan": p, "phone": {"preset": "x", "mount": {}}}
          for i, (s0, kmh, p) in enumerate([(300, 36, slow), (150, 72, fast), (0, 72, fast)])]
    ms = simulate_vehicles([Vehicle.model_validate(v) for v in vs], RoadMap(ROAD), 100.0, np.random.default_rng(1))
    for lead, f in pairwise(ms):
        k = f.t <= lead.t[-1]
        gap = np.interp(f.t[k], lead.t, lead.s) - f.s[k]
        assert gap.min() >= 15.0 - 1e-9 and f.v.min() >= 0 and f.v[k].min() < 1.0


def test_plan_points_are_met_at_their_position():
    plan = [
        {"type": "speed", "s": 400, "kmh": 36},  # slowdown: reached exactly at 400 m
        {"type": "speed", "s": 800, "kmh": 72},  # speed-up: starts at 800 m
        {"type": "stop", "s": 1500, "dwell_s": 5},
    ]
    m = _run(plan, jitter=0.0)  # no fluctuation: the target speed is read off directly
    assert abs(m.s[np.argmax(m.v < 10.0 + 0.05)] - 400) < 5
    later = m.s > 500  # the car starts at 72 km/h, so look only after the slowdown
    start = m.s[later][np.argmax(m.v[later] > 10.0 + 0.05)]
    assert 800 <= start < 805  # holds the speed until 800 m; the jerk-limited start gains 0.05 m/s within about 2 m
    still = np.flatnonzero(m.v == 0)
    assert abs(m.s[still[0]] - 1500) < 1 and abs((m.t[still[-1]] - m.t[still[0]]) - 5) < 0.2
