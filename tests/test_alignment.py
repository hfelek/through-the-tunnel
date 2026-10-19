import numpy as np

from sim.contracts.estimation import Measurement
from sim.contracts.preset import load_preset
from sim.contracts.scenario import load_scenario
from sim.estimators.alignment import Aligner
from sim.estimators.baseline import BaselineEstimator
from sim.runner import KINDS
from sim.sensors.gnss import generate_gnss
from sim.sensors.imu import _VEHICLE_TO_FLAT, MountPath, _mount_matrix, generate_imu
from sim.world.road import RoadMap
from sim.world.vehicle import simulate_vehicles

SCENARIOS = "scenarios"


def run_aligner(name, noise_free, stride=1):
    """Feed simulated measurements through an Aligner; s_est / v_est come from the baseline estimator, never truth."""
    sc = load_scenario(f"{SCENARIOS}/{name}.json")
    rm = RoadMap(sc.road)
    ms, *vs = np.random.SeedSequence(sc.seed).spawn(1 + len(sc.vehicles))
    motion = simulate_vehicles(sc.vehicles, rm, sc.rates_hz.imu, np.random.default_rng(ms))[0]
    veh = sc.vehicles[0]
    preset, ph = load_preset(veh.phone.preset), veh.phone
    r_imu, r_gnss = (np.random.default_rng(c) for c in vs[0].spawn(len(KINDS))[:2])
    path = MountPath(ph.mount, ph.handling_events, r_imu)
    imu = generate_imu(motion, ph.mount, ph.handling_events, preset, r_imu, noise_free=noise_free, path=path)
    if noise_free:  # exact fixes at 1 Hz outside tunnels
        t = np.arange(int(motion.t[-1]) + 1, dtype=float)
        s, v = np.interp(t, motion.t, motion.s), np.interp(t, motion.t, motion.v)
        keep = ~rm.in_tunnel(s)
        pos = rm.at(s)
        gnss = {"t": t[keep], "x": pos["x"][keep], "y": pos["y"][keep], "z": pos["z"][keep], "speed": v[keep],
                "course": pos["heading"][keep], "h_acc": np.full(keep.sum(), 1.0), "speed_acc": np.full(keep.sum(), 0.1)}
    else:
        gnss = generate_gnss(motion, rm, sc.gnss_env, preset, sc.rates_hz.gnss, r_gnss)
    stream = [(t, 1, "gnss", {k: gnss[k][i] for k in gnss if k != "t"}) for i, t in enumerate(gnss["t"].tolist())]
    stream += [(t, 0, "imu", {k: imu[k][i] for k in imu if k != "t"}) for i, t in enumerate(imu["t"].tolist())]
    stream.sort(key=lambda x: (x[0], x[1]))
    base, al = BaselineEstimator(), Aligner(rm)
    base.reset(rm, {})
    out, last, last_active = [], None, None
    al.snaps = []  # (t of the mode change, the mode that ended, its alignment): for inspection
    for t, _, kind, data in stream:
        m = Measurement(t=t, kind=kind, data=data)
        if kind == "gnss":
            base.update(m)
            al.process_gnss(m)
        else:
            e = base.estimate(t)
            out.append(al.process_imu(m, e.s, e.v))
            if out[-1].mode != last and last is not None:
                al.snaps.append((t, last, last_active))
            last, last_active = out[-1].mode, al.active
    return sc, al, out, motion


def true_m(mount):
    return _VEHICLE_TO_FLAT.T @ _mount_matrix(mount)  # phone -> vehicle; rows are (f, l, u)


def angle_deg(a, b):
    return float(np.degrees(np.arccos(np.clip(a @ b, -1.0, 1.0))))


def test_mount_yaw_and_gyro_bias_found_noise_free():
    sc, al, out, _ = run_aligner("curved_5km_exit_inside", noise_free=True)
    m = true_m(sc.vehicles[0].phone.mount)
    assert al.mode == "aligned" and out[-1].valid
    assert angle_deg(al.active.f, m[0]) < 1.0 and angle_deg(al.active.u, m[2]) < 1.0
    assert np.all(np.abs(np.degrees(al.b_g)) < 0.01)


def test_handling_detected_and_mount_realigned_noise_free():
    sc, al, out, _ = run_aligner("phone_handled_mid_tunnel", noise_free=True)
    ev = sc.vehicles[0].phone.handling_events[0]
    assert len(al.hand_log) == 1 and abs(al.hand_log[0][0] - ev.t) < 1.0
    assert any(o.mode == "in_hand" and not o.valid for o in out) and out[-1].mode in ("realigned", "aligned")
    m = true_m(ev.new_mount)
    assert angle_deg(al.active.f, m[0]) < 1.0 and angle_deg(al.active.u, m[2]) < 1.0
    assert run_aligner("hard_brake_inside", noise_free=True)[1].hand_log == []
