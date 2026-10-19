import numpy as np

from sim.contracts.preset import load_preset
from sim.contracts.scenario import HandlingEvent, Mount, Road, Vehicle
from sim.sensors.imu import MountPath, _exp, _log, _mount_matrix, generate_imu
from sim.world.road import RoadMap
from sim.world.vehicle import simulate_vehicle

ROAD = Road(start_heading_deg=0, segments=[{"type": "straight", "length_m": 3000, "grade_pct": 0}])
MOUNT, NEW = Mount(yaw_deg=4, pitch_deg=65, roll_deg=-2), Mount(yaw_deg=6, pitch_deg=60, roll_deg=0)


def test_integrated_gyro_recovers_mount_change():
    veh = Vehicle.model_validate({
        "id": "v", "start_s": 0, "initial_kmh": 72, "phone": {"preset": "x", "mount": {}},
        "profile": [{"type": "cruise", "kmh": 72, "until_s": 3000}],
    })
    motion = simulate_vehicle(veh, RoadMap(ROAD), 100.0, np.random.default_rng(1))
    dt = float(motion.t[1] - motion.t[0])
    for t0, dur in ((20.0, 4.0), (20.0, 120.0)):  # the long one includes re-orientations
        ev = [HandlingEvent(t=t0, duration_s=dur, new_mount=NEW)]
        path = MountPath(MOUNT, ev, np.random.default_rng(3))
        imu = generate_imu(motion, MOUNT, ev, load_preset("flagship_2024"), np.random.default_rng(3), noise_free=True, path=path)
        w = np.stack([imu["gx"], imu["gy"], imu["gz"]], axis=1)
        i0, i1 = round(t0 / dt), round((t0 + dur) / dt)
        r = np.eye(3)
        for k in range(i0, i1):  # straight road: the gyro is the mount path's rotation alone
            r = r @ _exp(w[k] * dt)
        err = np.degrees(np.linalg.norm(_log(r.T @ (_mount_matrix(MOUNT).T @ _mount_matrix(NEW)))))
        assert err < 0.1
