"""Smartphone GNSS model (PLAN T3.3): 1 Hz fixes with correlated error, portal degradation and tunnel outages."""
import numpy as np

from sim.contracts.preset import Preset
from sim.contracts.scenario import GnssEnv
from sim.world.road import RoadMap
from sim.world.vehicle import VehicleMotion

VERTICAL_RATIO = 1.5  # A18
PORTAL_GROWTH = 5.0  # A19: error and h_acc factor right at a portal
RADIAL_68 = float(np.sqrt(-2.0 * np.log(1.0 - 0.68)))  # 1.5096: radial 68% of a circular Gaussian, in per-axis sigmas
MIN_COURSE_SPEED_MPS = 0.5  # below this the course is held and sigma_course = speed_std / 0.5 rad


def _portal_factor(road_map: RoadMap, s: np.ndarray, reach_m: float) -> np.ndarray:
    """Error growth factor 1..PORTAL_GROWTH, linear in the distance to the nearest portal (A19)."""
    if reach_m <= 0 or not road_map.tunnels:
        return np.ones_like(s)
    d = np.min([np.minimum(abs(s - t.start_s), abs(s - t.end_s)) for t in road_map.tunnels], axis=0)
    return 1.0 + (PORTAL_GROWTH - 1.0) * np.clip(1.0 - d / reach_m, 0.0, 1.0)


def _gauss_markov(n: int, dt: float, corr_time: float, rng: np.random.Generator) -> np.ndarray:
    """Unit-variance first-order Gauss-Markov process per axis (n, 3), started in its stationary distribution."""
    phi = np.exp(-dt / corr_time)
    w = rng.normal(size=(n, 3))
    e = np.empty((n, 3))
    e[0] = w[0]
    for i in range(1, n):
        e[i] = phi * e[i - 1] + np.sqrt(1.0 - phi**2) * w[i]
    return e


def _availability(inside: np.ndarray, t: np.ndarray, env: GnssEnv, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """(fix available, fix is one of the bad fixes after a tunnel exit) per grid time."""
    ok, bad = np.zeros(len(t), dtype=bool), np.zeros(len(t), dtype=bool)
    was_inside, hold_until, bad_left = False, -np.inf, 0
    for i, ti in enumerate(t):
        if inside[i]:
            was_inside = True
            continue
        if was_inside:  # first sample after leaving a tunnel
            was_inside, hold_until, bad_left = False, ti + rng.uniform(*env.reacquire_delay_s), env.bad_fixes_after_exit
        if ti < hold_until:
            continue
        ok[i], bad[i] = True, bad_left > 0
        bad_left = max(bad_left - 1, 0)
    return ok, bad


def generate_gnss(
    motion: VehicleMotion, road_map: RoadMap, env: GnssEnv, preset: Preset, rate_hz: float, rng: np.random.Generator,
) -> dict[str, np.ndarray]:
    """GNSS columns (t, x, y, z, speed, course, h_acc, speed_acc); only times with a fix are present."""
    dt = 1.0 / rate_hz
    t = motion.t[0] + dt * np.arange(int(np.floor((motion.t[-1] - motion.t[0]) / dt + 1e-9)) + 1)
    s, v = np.interp(t, motion.t, motion.s), np.interp(t, motion.t, motion.v)
    pos = road_map.at(s)
    g = preset.gnss
    # all random draws first, so the stream does not depend on which fixes exist
    unit = _gauss_markov(len(t), dt, g.position_corr_time.value, rng)
    ok, bad = _availability(road_map.in_tunnel(s), t, env, rng)
    bad_dir = rng.uniform(0.0, 2 * np.pi, len(t))
    speed_noise, course_noise = rng.normal(size=len(t)), rng.normal(size=len(t))

    sigma = g.position_std.value * _portal_factor(road_map, s, env.portal_degrade_m)  # per-axis horizontal sigma
    err = unit * sigma[:, None] * np.array([1.0, 1.0, VERTICAL_RATIO])  # A18
    err[:, 0] += bad * env.bad_fix_error_m * np.cos(bad_dir)
    err[:, 1] += bad * env.bad_fix_error_m * np.sin(bad_dir)
    h_acc = RADIAL_68 * sigma  # radial 68% horizontal accuracy, as Android and iOS report it
    h_acc = np.where(bad, np.hypot(h_acc, env.bad_fix_error_m), h_acc)  # honest: the receiver reports the larger error

    speed_std = g.speed_std.value
    course = pos["heading"] + course_noise * speed_std / np.maximum(v, MIN_COURSE_SPEED_MPS)
    held = None
    for i in np.flatnonzero(ok):  # hold the last course while (almost) standing still
        if v[i] < MIN_COURSE_SPEED_MPS and held is not None:
            course[i] = held
        held = course[i]
    course = (course + np.pi) % (2 * np.pi) - np.pi

    k = ok
    return {
        "t": t[k], "x": pos["x"][k] + err[k, 0], "y": pos["y"][k] + err[k, 1], "z": pos["z"][k] + err[k, 2],
        "speed": np.maximum(v + speed_noise * speed_std, 0.0)[k], "course": course[k],
        "h_acc": h_acc[k], "speed_acc": np.full(int(k.sum()), speed_std),
    }
