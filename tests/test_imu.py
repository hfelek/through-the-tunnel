import numpy as np
import pytest
from pydantic import ValidationError

from sim.contracts.preset import PRESET_DIR, Preset, load_preset
from sim.contracts.scenario import HandlingEvent, Mount, Road, Vehicle
from sim.sensors.imu import G, MountPath, generate_imu, imu_to_vehicle_accel
from sim.world.road import RoadMap
from sim.world.vehicle import simulate_vehicle

ROAD = Road(
    start_heading_deg=0,
    segments=[
        {"type": "straight", "length_m": 500, "grade_pct": 3},
        {"type": "arc", "length_m": 600, "radius_m": 400, "turn": "left", "grade_pct": 0},
    ],
)
MOUNT = Mount(yaw_deg=4, pitch_deg=65, roll_deg=-2)


def _motion(initial_kmh=72.0):
    profile = [{"type": "cruise", "kmh": initial_kmh, "until_s": 1100}] if initial_kmh else [{"type": "stop", "at_s": 0, "decel_mps2": 1.5, "dwell_s": 10}]
    veh = Vehicle.model_validate({
        "id": "v", "start_s": 0, "initial_kmh": initial_kmh, "phone": {"preset": "x", "mount": {}}, "profile": profile,
    })
    return simulate_vehicle(veh, RoadMap(ROAD), 100.0, np.random.default_rng(1))


@pytest.mark.parametrize("name", sorted(p.stem for p in PRESET_DIR.glob("*.json")))
def test_presets_validate(name):
    assert load_preset(name).id == name


def test_preset_requires_source():
    data = load_preset("budget").model_dump()
    data["accel"]["noise_density"]["source"] = ""
    with pytest.raises(ValidationError):
        Preset.model_validate(data)


def test_rest_norm_and_curve_gyro():
    preset, rng = load_preset("flagship_2024"), np.random.default_rng(0)
    m = _motion(0.0)
    imu = generate_imu(m, MOUNT, [], preset, rng, noise_free=True)
    n = np.sqrt(imu["ax"] ** 2 + imu["ay"] ** 2 + imu["az"] ** 2)
    assert abs(n[0] - G * 1.0) < 0.05 * G  # grade only tilts gravity, norm stays g
    m = _motion()
    imu = generate_imu(m, Mount(), [], preset, rng, noise_free=True)
    curve = m.s > 600  # inside the arc, away from the grade blend
    np.testing.assert_allclose(imu["gz"][curve], (m.v / 400)[curve], atol=1e-6)


def test_noise_free_inverse_returns_true_acceleration():
    preset, rng = load_preset("flagship_2024"), np.random.default_rng(0)
    m = _motion()
    ev = [HandlingEvent(t=5, duration_s=4, new_mount=Mount(pitch_deg=20))]
    path = MountPath(MOUNT, ev, rng)
    imu = generate_imu(m, MOUNT, ev, preset, rng, noise_free=True, path=path)
    a = imu_to_vehicle_accel(imu, m, path)
    np.testing.assert_allclose(a, np.stack([m.a, m.a_lat, m.a_vert], axis=1), atol=1e-9)
