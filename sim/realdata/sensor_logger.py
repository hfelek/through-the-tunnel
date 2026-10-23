"""Sensor Logger (iOS, CSV export) -> trace with source "real" (docs/CONTRACTS.md 3.3).

iOS conversion lives here only (CONTRACTS 3.1): the accelerometer reports -g on a face-up phone, so specific force is
-G times the raw value (a face-up phone then reads +9.7 on z); the gyro keeps its axes and sign; lat/lon become local
ENU and the compass bearing becomes an ENU heading. The map is built from the drive's own GNSS track (A2), so the
"truth" is the GNSS projected on that map (about 5 m accurate): the trace carries only truth t, s, v.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from scipy.interpolate import UnivariateSpline

from sim.contracts.trace import (
    Gnss,
    Imu,
    MapColumns,
    Measurements,
    Trace,
    Truth,
    VehicleTrace,
    read_trace,
    write_trace,
)
from sim.world.road import Centerline, RoadMap

G = 9.80665  # m/s^2, standard gravity: iOS reports acceleration in g
EARTH_R = 6378137.0  # m, WGS-84 equatorial radius; local flat-earth ENU is good to well under 1 m over a few km
DEFAULT_SPAN_S = (110.0, 830.0)  # the city drive without the parked start and end (T10 check)
ROOT = Path(__file__).resolve().parents[2]
REAL_DIR = ROOT / "data" / "real"
CACHE_DIR = REAL_DIR / "cache"


def _csv(folder: Path, name: str) -> dict[str, np.ndarray]:
    """One Sensor Logger CSV as float columns sorted by time; empty cells become NaN."""
    matches = [p for p in folder.glob("*.csv") if p.name == f"{name}.csv" or p.name.endswith(f"_{name}.csv")]
    with open(matches[0], newline="") as f:
        rows = list(csv.DictReader(f))
    cols = {k: np.array([float(r[k]) if r[k] != "" else np.nan for r in rows]) for k in rows[0]}
    order = np.argsort(cols["seconds_elapsed"], kind="stable")
    return {k: v[order] for k, v in cols.items()}


def load_arrays(folder: Path, t0: float, t1: float) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """IMU and GNSS arrays in contract units, time counted from t0."""
    au, gy, loc = (_csv(folder, n) for n in ("AccelerometerUncalibrated", "GyroscopeUncalibrated", "Location"))
    t = au["seconds_elapsed"]
    m = (t >= t0) & (t <= t1)
    imu = {"t": t[m] - t0, "ax": -G * au["x"][m], "ay": -G * au["y"][m], "az": -G * au["z"][m]}
    for c in "xyz":  # the gyro has its own timestamps: resample onto the accelerometer's
        imu["g" + c] = np.interp(t[m], gy["seconds_elapsed"], gy[c])
    # speed or bearing < 0 means "invalid" in Core Location; NaN fails both tests too
    k = (loc["seconds_elapsed"] >= t0) & (loc["seconds_elapsed"] <= t1) & (loc["speed"] >= 0) & (loc["bearing"] >= 0)
    loc = {n: v[k] for n, v in loc.items()}
    lat0, lon0 = np.deg2rad(loc["latitude"][0]), np.deg2rad(loc["longitude"][0])
    gnss = {
        "t": loc["seconds_elapsed"] - t0,
        "x": EARTH_R * np.cos(lat0) * (np.deg2rad(loc["longitude"]) - lon0),
        "y": EARTH_R * (np.deg2rad(loc["latitude"]) - lat0),
        "z": loc["altitude"] - loc["altitude"][0],
        "speed": loc["speed"],
        "course": np.pi / 2 - np.deg2rad(loc["bearing"]),  # compass bearing (clockwise from north) -> ENU (CCW from east)
        "h_acc": loc["horizontalAccuracy"],
        "speed_acc": np.maximum(loc["speedAccuracy"], 0.05),  # iOS reports 0 or -1 for "unknown"
    }
    return imu, gnss


def _moving_mean(x: np.ndarray, k: int) -> np.ndarray:
    """Centered moving average over k samples (odd), shorter windows at the ends."""
    return np.convolve(x, np.ones(k), "same") / np.convolve(np.ones(len(x)), np.ones(k), "same")


def build_map(g: dict[str, np.ndarray], smooth: float = 0.1, smooth_z: float = 4.0, k_win: int = 31) -> RoadMap:
    """Smoothing spline through the GNSS track, resampled at 1 m; grade from the GNSS altitude."""
    t, v = g["t"], g["speed"]
    s = np.concatenate([[0], np.cumsum(0.5 * (v[1:] + v[:-1]) * np.diff(t))])  # distance driven, from the speed
    keep = np.concatenate([[True], np.diff(s) > 0.5])  # drop repeated fixes at standstill
    S, w = s[keep], 1 / np.maximum(g["h_acc"][keep], 1)  # weight a fix by 1 / its accuracy
    sx = UnivariateSpline(S, g["x"][keep], w=w, s=len(S) * smooth)
    sy = UnivariateSpline(S, g["y"][keep], w=w, s=len(S) * smooth)
    sz = UnivariateSpline(S, g["z"][keep], s=len(S) * smooth_z)
    u = np.linspace(S[0], S[-1], 400000)  # the spline parameter is the driven distance, not the arc length of the fit
    arc = np.concatenate([[0], np.cumsum(np.hypot(np.diff(sx(u)), np.diff(sy(u))))])
    sn = np.arange(0, arc[-1], 1.0)
    un = np.interp(sn, arc, u)
    h = np.unwrap(np.arctan2(sy.derivative()(un), sx.derivative()(un)))
    curvature = _moving_mean(np.gradient(h, sn), k_win)  # raw heading derivative is noisy
    z = sz(un)
    grade = _moving_mean(np.gradient(z, sn), 51)
    return RoadMap.from_columns(Centerline(sn, sx(un), sy(un), z, h, curvature, grade))


def convert(folder: Path, t0: float = DEFAULT_SPAN_S[0], t1: float = DEFAULT_SPAN_S[1]) -> Trace:
    """The recording as a trace: map from the GNSS track, imu and gnss, partial truth (t, s, v) = GNSS on the map."""
    imu, g = load_arrays(folder, t0, t1)
    rm = build_map(g)
    line = rm.line
    cols = {n: getattr(line, n).tolist() for n in ("s", "x", "y", "z", "heading", "curvature", "grade")}
    truth = Truth(t=g["t"].tolist(), s=rm.project(g["x"], g["y"]).tolist(), v=g["speed"].tolist())
    meas = Measurements(
        imu=Imu(**{c: a.tolist() for c, a in imu.items()}), gnss=Gnss(**{c: a.tolist() for c, a in g.items()}),
    )
    return Trace(
        source="real", scenario_id=f"real_{folder.name}", map=MapColumns(**cols),
        vehicles=[VehicleTrace(id="car1", truth=truth, measurements=meas)],
    )


def list_recordings(root: Path = REAL_DIR) -> list[str]:
    """Folder names under data/real that look like a Sensor Logger export (raw/ is the unconverted drop folder)."""
    return sorted(p.name for p in root.iterdir() if p.is_dir() and (p / "Location.csv").is_file())


def load_recording(rec_id: str, root: Path = REAL_DIR, span: tuple[float, float] = DEFAULT_SPAN_S) -> Trace:
    """The converted trace, from the JSON cache when it exists (the conversion takes a few seconds)."""
    cache = CACHE_DIR / f"{rec_id}_{span[0]:g}_{span[1]:g}.json"
    if cache.is_file():
        return read_trace(cache)
    trace = convert(root / rec_id, *span)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    write_trace(trace, cache)
    return trace


def map_of(trace: Trace) -> RoadMap:
    """Rebuild the RoadMap from the trace's map columns."""
    m = trace.map
    return RoadMap.from_columns(Centerline(*(np.array(getattr(m, n)) for n in ("s", "x", "y", "z", "heading", "curvature", "grade"))))
