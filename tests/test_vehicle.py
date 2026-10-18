import numpy as np

from sim.contracts.scenario import Road, Vehicle
from sim.world.road import RoadMap
from sim.world.vehicle import simulate_vehicle

ROAD = Road(
    start_heading_deg=0,
    segments=[
        {"type": "straight", "length_m": 1000},
        {"type": "arc", "length_m": 800 * np.pi / 2, "radius_m": 800, "turn": "left"},
    ],
)


def _vehicle(profile, jitter=2.0):
    return Vehicle.model_validate({
        "id": "v", "start_s": 0, "initial_kmh": 72, "speed_jitter_kmh": jitter, "profile": profile,
        "phone": {"preset": "x", "mount": {}},
    })


def _run(profile, seed=1, jitter=2.0):
    return simulate_vehicle(_vehicle(profile, jitter), RoadMap(ROAD), 100.0, np.random.default_rng(seed))


STOP = [
    {"type": "cruise", "kmh": 72, "until_s": 300},
    {"type": "stop", "at_s": 600, "decel_mps2": 2.0, "dwell_s": 5},
    {"type": "cruise", "kmh": 72, "until_s": 1200},
]


def test_stop_exact_and_nonnegative():
    m = _run(STOP)
    i = np.flatnonzero(m.v == 0)
    assert m.v.min() >= 0 and abs(m.s[i[0]] - 600) < 1e-6
    assert abs((m.t[i[-1]] - m.t[i[0]]) - 5) < 0.02 and m.s[-1] == ROAD.length_m


def test_same_seed_same_result():
    assert np.array_equal(_run(STOP, 3).v, _run(STOP, 3).v)
    assert not np.array_equal(_run(STOP, 3).v, _run(STOP, 4).v)


def test_lateral_acceleration_in_curve():
    m = _run([{"type": "cruise", "kmh": 72, "until_s": 1200}])
    k = (m.s > 1100) & (m.s < 2000)
    assert np.allclose(m.a_lat[k], m.v[k] ** 2 / 800)
