"""Replay a Sensor Logger recording (iOS, CSV export) through the estimators with an artificial GNSS outage.

Raw recordings stay out of the repository (they contain a real location trace); put the CSV files in one folder and run:

    python tools/replay_real.py data/real/raw/<folder> --outage 515 625 --start 110 --end 830

What it does (written for the T10 check, not part of the simulator):
- converts iOS units and signs to the contract (CONTRACTS 3.1): specific force in m/s^2 (iOS reports -g on a face-up
  phone), gyro in rad/s (same axes and sign), GNSS lat/lon to local ENU, compass bearing to ENU heading;
- builds the map from the drive's own GNSS track (smoothing spline, resampled at 1 m; grade from GNSS altitude), i.e. it
  assumes a map as good as the drive's GNSS (A2);
- removes the GNSS fixes inside the outage window and declares that stretch a tunnel;
- "truth" inside the window is the removed GNSS, projected on the map (about 5 m accuracy).
--relax uses calibration conditions that real hilly, curved roads can meet (flat grade 3%, straight radius 500 m);
--bias-rw overrides the EKF's bias random walk.
"""
import argparse
import glob
import os

import numpy as np
import pandas as pd
from scipy.interpolate import UnivariateSpline

from sim.contracts.scenario import Road, Tunnel
from sim.estimators.alignment import Aligner
from sim.runner import _run_estimators
from sim.world.road import Centerline, RoadMap

G = 9.80665


def _csv(folder: str, name: str) -> pd.DataFrame:
    path = [p for p in glob.glob(os.path.join(folder, "*.csv")) if p.endswith(f"_{name}.csv") or os.path.basename(p) == f"{name}.csv"]
    return pd.read_csv(path[0]).sort_values("seconds_elapsed").reset_index(drop=True)


def load(folder: str, t0: float, t1: float):
    au, gy, loc = _csv(folder, "AccelerometerUncalibrated"), _csv(folder, "GyroscopeUncalibrated"), _csv(folder, "Location")
    t = au.seconds_elapsed.values
    m = (t >= t0) & (t <= t1)
    imu = {"t": t[m] - t0, "ax": -G * au.x.values[m], "ay": -G * au.y.values[m], "az": -G * au.z.values[m]}
    for c in "xyz":
        imu["g" + c] = np.interp(t[m], gy.seconds_elapsed, gy[c])
    loc = loc[(loc.seconds_elapsed >= t0) & (loc.seconds_elapsed <= t1) & (loc.speed >= 0) & (loc.bearing >= 0)]
    lat0, lon0, r = np.deg2rad(loc.latitude.iloc[0]), np.deg2rad(loc.longitude.iloc[0]), 6378137.0
    gnss = {
        "t": loc.seconds_elapsed.values - t0,
        "x": (r * np.cos(lat0) * (np.deg2rad(loc.longitude) - lon0)).values,
        "y": (r * (np.deg2rad(loc.latitude) - lat0)).values,
        "z": (loc.altitude - loc.altitude.iloc[0]).values,
        "speed": loc.speed.values,
        "course": np.pi / 2 - np.deg2rad(loc.bearing.values),
        "h_acc": loc.horizontalAccuracy.values,
        "speed_acc": loc.speedAccuracy.clip(lower=0.05).values,
    }
    return imu, gnss


def build_map(g: dict, smooth: float = 0.1, smooth_z: float = 4.0, k_win: int = 31) -> RoadMap:
    t, v = g["t"], g["speed"]
    s = np.concatenate([[0], np.cumsum(0.5 * (v[1:] + v[:-1]) * np.diff(t))])
    keep = np.concatenate([[True], np.diff(s) > 0.5])  # drop repeated fixes at standstill
    S, w = s[keep], 1 / np.maximum(g["h_acc"][keep], 1)
    sx = UnivariateSpline(S, g["x"][keep], w=w, s=len(S) * smooth)
    sy = UnivariateSpline(S, g["y"][keep], w=w, s=len(S) * smooth)
    sz = UnivariateSpline(S, g["z"][keep], s=len(S) * smooth_z)
    u = np.linspace(S[0], S[-1], 400000)
    arc = np.concatenate([[0], np.cumsum(np.hypot(np.diff(sx(u)), np.diff(sy(u))))])
    sn = np.arange(0, arc[-1], 1.0)
    un = np.interp(sn, arc, u)
    h = np.unwrap(np.arctan2(sy.derivative()(un), sx.derivative()(un)))
    k = pd.Series(np.gradient(h, sn)).rolling(k_win, center=True, min_periods=1).mean().values
    z = sz(un)
    grade = pd.Series(np.gradient(z, sn)).rolling(51, center=True, min_periods=1).mean().values
    rm = RoadMap(Road(start_heading_deg=0, segments=[{"type": "straight", "length_m": float(sn[-1])}]))
    rm.line, rm.length_m = Centerline(sn, sx(un), sy(un), z, h, k, grade), float(sn[-1])
    return rm


def replay(imu, g, rm, ta, tb, estimators):
    s_fix = rm.project(g["x"], g["y"])
    rm.tunnels = [Tunnel(id="T1", start_s=float(np.interp(ta, g["t"], s_fix)), end_s=float(np.interp(tb, g["t"], s_fix)))]
    keep = (g["t"] < ta) | (g["t"] > tb)
    sensors = {"imu": imu, "gnss": {k: np.asarray(v)[keep] for k, v in g.items()}}
    res, _ = _run_estimators(rm, sensors, 0.0, float(min(tb + 60, imu["t"][-1])), 10.0, estimators)
    out = {}
    for key, c in res.items():
        t, s, sig = np.array(c.t), np.array(c.s), np.array(c.sigma_s)
        err = s - np.interp(t, g["t"], s_fix)
        w, i = (t >= ta) & (t <= tb), int(np.searchsorted(t, tb))
        out[key] = {"exit_error_m": float(err[i]), "sigma_m": float(sig[i]),
                    "consistency_pct": float(100 * np.mean(np.abs(err[w]) < 2 * sig[w])), "t": t, "err": err, "sig": sig}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--outage", nargs=2, type=float, required=True, help="start and end, s since recording start")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=1e9)
    ap.add_argument("--relax", action="store_true")
    ap.add_argument("--bias-rw", type=float, default=None)
    a = ap.parse_args()
    if a.relax:
        Aligner.default_params.update({"flat_grade": 0.03, "straight_curvature": 2e-3})
    imu, g = load(a.folder, a.start, a.end)
    params = {} if a.bias_rw is None else {"bias_rw": a.bias_rw}
    est = {k: (params if k != "baseline" else {}) for k in ("baseline", "ekf", "ekf_zupt", "pf")}
    out = replay(imu, g, build_map(g), a.outage[0] - a.start, a.outage[1] - a.start, est)
    for k, r in out.items():
        print(f"{k:9s} exit error {r['exit_error_m']:+8.1f} m  sigma {r['sigma_m']:6.1f} m  consistency {r['consistency_pct']:5.1f}%")


if __name__ == "__main__":
    main()
