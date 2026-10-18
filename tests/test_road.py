import numpy as np

from sim.contracts.scenario import Road
from sim.world.road import RoadMap


def _map(segments, tunnels=()):
    return RoadMap(Road(start_heading_deg=0, segments=segments, tunnels=list(tunnels)))


def test_length_and_grade():
    m = _map([{"type": "straight", "length_m": 1000, "grade_pct": 3}, {"type": "straight", "length_m": 500}])
    assert m.length_m == 1500
    assert abs(float(m.at(1000)["z"]) - 30) < 1e-6


def test_arc_heading_and_projection():
    m = _map([{"type": "straight", "length_m": 300}, {"type": "arc", "length_m": 800 * np.pi / 2, "radius_m": 800, "turn": "left"}])
    h = m.at(m.length_m)["heading"] - m.at(0)["heading"]
    assert abs(np.degrees(h) - 90) < 1e-6
    s = np.array([0.0, 150.3, 300.0, 700.7, m.length_m])
    p = m.at(s)
    assert np.all(np.abs(m.project(p["x"], p["y"]) - s) < 0.5)


def test_in_tunnel():
    m = _map([{"type": "straight", "length_m": 1000}], [{"id": "T", "start_s": 200, "end_s": 400}])
    assert m.in_tunnel(300) and not m.in_tunnel(500)
