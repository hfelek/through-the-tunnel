import numpy as np

from sim.contracts.preset import load_preset
from sim.contracts.scenario import GnssEnv, Road
from sim.sensors.gnss import generate_gnss
from sim.world.road import RoadMap
from sim.world.vehicle import VehicleMotion

V = 100 / 3.6
ENV = GnssEnv(portal_degrade_m=60, reacquire_delay_s=(2, 6), bad_fixes_after_exit=3, bad_fix_error_m=25)
ROAD = Road(
    start_heading_deg=0, segments=[{"type": "straight", "length_m": 150_000}],
    tunnels=[{"id": "T1", "start_s": 20_000, "end_s": 21_000}],
)
PRESET = load_preset("flagship_2024")


def _motion(n=5000 * 10):
    t = np.arange(n) / 10.0
    z = np.zeros(n)
    return VehicleMotion(t=t, s=V * t, v=z + V, a=z, yaw=z, yaw_rate=z, pitch=z, a_lat=z, a_vert=z)


def _fixes(seed=0):
    g = generate_gnss(_motion(), RoadMap(ROAD), ENV, PRESET, 1.0, np.random.default_rng(seed))
    return g, V * g["t"]  # the road runs east: x is along-track, y is cross-track


def test_no_fixes_inside_tunnel_and_bad_fixes_after_exit():
    g, s_true = _fixes()
    assert not ((s_true > 20_000) & (s_true < 21_000)).any()
    t_exit = 21_000 / V
    after = g["t"] > t_exit
    assert 2 <= g["t"][after][0] - t_exit <= 6 + 1  # reacquire delay range plus one grid step
    off = np.hypot(g["x"] - s_true, g["y"])[after][:3]
    assert (off > 15).all() and (off < 40).all()
    assert (g["h_acc"][after][:3] > 20).all()


def test_open_sky_error_matches_preset():
    g, s_true = _fixes()
    sky = np.abs(s_true - 20_500) > 5_000
    err = np.r_[(g["x"] - s_true)[sky], g["y"][sky]]
    assert abs(np.std(err) / PRESET.gnss.position_std.value - 1) < 0.15
    assert np.all(np.abs(g["course"][sky]) < 0.1) and (g["h_acc"][sky] == PRESET.gnss.position_std.value).all()
