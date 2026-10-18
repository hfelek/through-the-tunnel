"""Smartphone barometer model (PLAN T3.4): standard-atmosphere pressure, noise, drift, tunnel step and fan fluctuation."""
import numpy as np

from sim.contracts.preset import Preset
from sim.contracts.scenario import TunnelEnv
from sim.world.road import RoadMap
from sim.world.vehicle import VehicleMotion

BASE_ALTITUDE_M = 0.0  # A20
TAU_STEP_S = 1.0  # A21: settling time of the tunnel pressure step at entry and exit
TAU_FAN_S = 10.0  # A22: correlation time of the fan-driven fluctuation
SEA_LEVEL_HPA = 1013.25  # ICAO Standard Atmosphere (Doc 7488) / US Standard Atmosphere 1976
PA_PER_HPA = 100.0


def pressure_hpa(altitude_m: np.ndarray) -> np.ndarray:
    """ISA troposphere pressure: p = p0 (1 - 2.25577e-5 h)^5.25588 (ICAO Doc 7488 / US Std Atmosphere 1976)."""
    return SEA_LEVEL_HPA * (1.0 - 2.25577e-5 * altitude_m) ** 5.25588


def _step_pa(t: np.ndarray, s_true: np.ndarray, road_map: RoadMap, step_pa: float) -> np.ndarray:
    """Tunnel pressure step: exponential rise after each entry, exponential decay after each exit (A21)."""
    dp = np.zeros_like(t)
    for tun in road_map.tunnels:
        i_in, i_out = np.searchsorted(s_true, [tun.start_s, tun.end_s])  # s_true is non-decreasing
        if i_in >= len(t):
            continue
        t_in = t[i_in]
        end = t[i_out] if i_out < len(t) else np.inf
        inside = (t >= t_in) & (t < end)
        dp[inside] += step_pa * (1.0 - np.exp(-(t[inside] - t_in) / TAU_STEP_S))
        if np.isfinite(end):
            after = t >= end
            dp[after] += step_pa * (1.0 - np.exp(-(end - t_in) / TAU_STEP_S)) * np.exp(-(t[after] - end) / TAU_STEP_S)
    return dp


def _fan_pa(inside: np.ndarray, dt: float, sigma_pa: float, w: np.ndarray) -> np.ndarray:
    """Gauss-Markov fluctuation with stationary std sigma_pa, active only inside a tunnel, 0 at each entry (A22)."""
    phi = np.exp(-dt / TAU_FAN_S)
    x = np.zeros(len(w))
    for i in range(1, len(w)):
        if inside[i]:
            x[i] = phi * x[i - 1] + sigma_pa * np.sqrt(1.0 - phi**2) * w[i]
    return x


def generate_baro(
    motion: VehicleMotion, road_map: RoadMap, env: TunnelEnv, preset: Preset, rate_hz: float, rng: np.random.Generator,
    tunnel_effects: bool = True,
) -> dict[str, np.ndarray]:
    """Baro columns (t, p_hpa) on a regular grid; noise and drift are always on."""
    dt = 1.0 / rate_hz
    t = motion.t[0] + dt * np.arange(int(np.floor((motion.t[-1] - motion.t[0]) / dt + 1e-9)) + 1)
    s = np.interp(t, motion.t, motion.s)
    b = preset.baro
    # all random draws first, so the stream does not depend on the options
    white, walk, fan_w = rng.normal(size=len(t)), rng.normal(size=len(t)), rng.normal(size=len(t))

    p_pa = pressure_hpa(BASE_ALTITUDE_M + road_map.at(s)["z"]) * PA_PER_HPA
    p_pa += white * b.noise_std.value  # Pa
    walk[0] = 0.0
    p_pa += np.cumsum(walk * b.drift_random_walk.value * np.sqrt(dt))  # Pa/sqrt(s) * sqrt(s)
    if tunnel_effects:
        p_pa += _step_pa(t, s, road_map, env.pressure_step_pa)
        p_pa += _fan_pa(road_map.in_tunnel(s), dt, env.fan_pressure_noise_pa, fan_w)
    return {"t": t, "p_hpa": p_pa / PA_PER_HPA}
