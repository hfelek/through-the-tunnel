import numpy as np

from sim.contracts.preset import load_preset
from sim.contracts.scenario import Road, TunnelEnv
from sim.sensors.baro import generate_baro
from sim.world.road import RoadMap
from sim.world.vehicle import VehicleMotion

V = 20.0
ENV = TunnelEnv(pressure_step_pa=20, fan_pressure_noise_pa=8, mag_disturbance_ut=25)


def _motion(length_m, rate=10):
    t = np.arange(int(length_m / V * rate)) / rate
    z = np.zeros_like(t)
    return VehicleMotion(t=t, s=V * t, v=z + V, a=z, yaw=z, yaw_rate=z, pitch=z, a_lat=z, a_vert=z)


def _noiseless():
    preset = load_preset("flagship_2024").model_copy(deep=True)
    preset.baro.noise_std.value = 0.0
    preset.baro.drift_random_walk.value = 0.0
    return preset


def test_ten_metre_climb_drops_1_2_hpa():
    motion = _motion(1000)
    road = Road(start_heading_deg=0, segments=[{"type": "straight", "length_m": 1000, "grade_pct": 1}])
    rm = RoadMap(road)
    p = generate_baro(motion, rm, ENV, _noiseless(), 10.0, np.random.default_rng(0))["p_hpa"]
    climb = rm.at(motion.s[-1])["z"] - rm.at(motion.s[0])["z"]
    assert abs((p[0] - p[-1]) * 10.0 / climb - 1.20) < 0.02


def test_tunnel_effects_off_leaves_only_noise():
    road = Road(start_heading_deg=0, segments=[{"type": "straight", "length_m": 4000}],
                tunnels=[{"id": "T1", "start_s": 1000, "end_s": 3000}])
    rm, motion, preset = RoadMap(road), _motion(4000), load_preset("flagship_2024")
    on = generate_baro(motion, rm, ENV, preset, 10.0, np.random.default_rng(1))["p_hpa"]
    off = generate_baro(motion, rm, ENV, preset, 10.0, np.random.default_rng(1))["p_hpa"]
    off_fx = generate_baro(motion, rm, ENV, preset, 10.0, np.random.default_rng(1), tunnel_effects=False)["p_hpa"]
    assert np.array_equal(on, off) and not np.allclose(on, off_fx)
    outside = motion.s < 1000
    assert np.allclose(on[outside], off_fx[outside])  # identical outside the tunnel
    assert abs(np.std(np.diff(off_fx)) / 1.2e-2 / np.sqrt(2) - 1) < 0.3  # white noise 1.2 Pa dominates the increments
