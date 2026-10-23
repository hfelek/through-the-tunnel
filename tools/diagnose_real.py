"""Diagnosis of the real drive with an artificial tunnel (write-up section 6.3, Table 3).

Reproduces the numbers the write-up quotes for data/real/car_mounted:

1. Stops (GNSS speed < 0.5 m/s for at least 3 s) over the whole recording (0-830 s, times are recording times), the share
   of each stop the ZUPT detector flags as stationary and the idle vibration (median 1 s std of the accelerometer magnitude).
2. Four outage windows, exit error for both offset drift settings (bias_rw 5e-4 and 0.01), real-drive defaults.
3. In the default window 515-625 s: the EKF's speed against the GNSS speed, and the forward acceleration minus the
   GNSS-derived acceleration before, inside and after the window.
4. A counterfactual for the grade feedback: the aligner looks the grade up at the true position instead of the EKF's.

Steps 3 and 4 read the truth (the removed GNSS) and patch the aligner at run time. They are a diagnosis only: the
estimators themselves never see the truth.

    python tools/diagnose_real.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sim.estimators import alignment, ekf
from sim.estimators.stationary import StationaryDetector
from sim.realdata.replay import REAL_DEFAULTS, replay
from sim.realdata.sensor_logger import DEFAULT_SPAN_S, load_recording

REC = "car_mounted"
T0 = DEFAULT_SPAN_S[0]  # trace time = recording time - T0
WINDOWS = [(430, 515), (515, 625), (640, 740), (720, 820)]
DEFAULT = (515, 625)


def exit_errors(trace, a, b, bias_rw):
    p = {**REAL_DEFAULTS, "bias_rw": bias_rw}
    m = replay(trace, a - T0, b - T0, {"baseline": {}, "ekf": p, "ekf_zupt": p, "pf": p}).vehicles[0].metrics
    return {k: m[k]["exit_error_m"]["T1"] for k in m}


def idle_vibration(t, mag, a, b):
    """Median of the 1 s standard deviation of the accelerometer magnitude inside [a, b]: a centered 1 s window at every
    sample, 0.5 s left out at each end so that the window stays inside the stop."""
    h = round(0.5 / np.median(np.diff(t)))  # half a window in samples
    inside = np.flatnonzero((t >= a + 0.5) & (t <= b - 0.5))
    return float(np.median([mag[i - h:i + h].std() for i in inside]))


def stops(trace):
    """(start, end, % flagged stationary, idle vibration) per stop; trace time = recording time."""
    tt, v = np.asarray(trace.vehicles[0].truth.t), np.asarray(trace.vehicles[0].truth.v)
    imu = trace.vehicles[0].measurements.imu
    cols = [np.asarray(getattr(imu, k)) for k in ("t", "ax", "ay", "az", "gx", "gy", "gz")]
    t_imu = cols[0]
    mag = np.sqrt(cols[1] ** 2 + cols[2] ** 2 + cols[3] ** 2)
    det = StationaryDetector(0.05, 0.004)  # the EKF + ZUPT defaults
    flag = np.array([det.update(*(c[i] for c in cols)) for i in range(len(t_imu))])
    still, out, i = v < 0.5, [], 0
    while i < len(tt):
        if still[i]:
            j = i
            while j + 1 < len(tt) and still[j + 1]:
                j += 1
            if tt[j] - tt[i] >= 3.0:
                k = (t_imu >= tt[i]) & (t_imu <= tt[j])
                out.append((tt[i], tt[j], 100.0 * flag[k].mean(), idle_vibration(t_imu, mag, tt[i], tt[j])))
            i = j + 1
        else:
            i += 1
    return out


def default_window_trace(trace, grade_at_truth: bool):
    """EKF run in the default window; returns (exit error, per-sample t, v_ekf, a_long)."""
    truth = trace.vehicles[0].truth
    tt, ts = np.asarray(truth.t), np.asarray(truth.s)
    rec = []
    orig_align, orig_disp = alignment.Aligner.process_imu, ekf.EkfEstimator._advance_display

    def align(self, m, s_est, v_est):
        out = orig_align(self, m, float(np.interp(m.t, tt, ts)) if grade_at_truth else s_est, v_est)
        self._last = out
        return out

    def disp(self, dt):
        a = getattr(self.aligner, "_last", None)
        if type(self) is ekf.EkfEstimator and a is not None and a.valid:
            rec.append((a.t, float(self.x[1]), a.a_long, float(self.x[2])))
        return orig_disp(self, dt)

    alignment.Aligner.process_imu, ekf.EkfEstimator._advance_display = align, disp
    try:
        m = replay(trace, DEFAULT[0] - T0, DEFAULT[1] - T0, {"ekf": dict(REAL_DEFAULTS)}).vehicles[0].metrics
    finally:
        alignment.Aligner.process_imu, ekf.EkfEstimator._advance_display = orig_align, orig_disp
    return m["ekf"]["exit_error_m"]["T1"], np.array(rec)


def main():
    trace = load_recording(REC)
    truth = trace.vehicles[0].truth
    gt, gv = np.asarray(truth.t), np.asarray(truth.v)

    print("1. Stops (GNSS speed < 0.5 m/s for >= 3 s) and the share the ZUPT detector flags as stationary")
    for a, b, pct, vib in stops(load_recording(REC, span=(0.0, DEFAULT_SPAN_S[1]))):  # offset 0: recording times
        note = "  (before the analysed span)" if a < DEFAULT_SPAN_S[0] else ""
        print(f"   {a:5.0f}-{b:5.0f} s  ({b - a:3.0f} s)  detected {pct:3.0f}%  idle vibration {vib:.3f} m/s²{note}")

    print("\n2. Exit error (m) per outage window, real-drive defaults; bias_rw 5e-4 -> 0.01")
    for a, b in WINDOWS:
        e1, e2 = exit_errors(trace, a, b, 5e-4), exit_errors(trace, a, b, 0.01)
        print(f"   {a}-{b} s: baseline {e1['baseline']:+6.0f} | EKF {e1['ekf']:+6.0f} -> {e2['ekf']:+6.0f}"
              f" | EKF+ZUPT {e1['ekf_zupt']:+6.0f} -> {e2['ekf_zupt']:+6.0f} | PF {e1['pf']:+6.0f} -> {e2['pf']:+6.0f}")

    err, r = default_window_trace(trace, grade_at_truth=False)
    ta, tb = DEFAULT[0] - T0, DEFAULT[1] - T0
    print(f"\n3. Default window {DEFAULT[0]}-{DEFAULT[1]} s, EKF exit error {err:+.0f} m (bias_rw 5e-4)")
    for dt in (0, 20, 40, 60, 80, 100, 110):
        i = min(np.searchsorted(r[:, 0], ta + dt), len(r) - 1)
        print(f"   t+{dt:3d} s: EKF speed {r[i, 1]:5.1f} m/s, GNSS speed {np.interp(ta + dt, gt, gv):5.1f} m/s")
    _, rt = default_window_trace(trace, grade_at_truth=True)  # a_long with the grade at the true position
    t1 = np.arange(np.ceil(rt[0, 0]), rt[-1, 0])
    a_long = np.array([rt[(rt[:, 0] >= t) & (rt[:, 0] < t + 1), 2].mean() for t in t1])
    b_ekf = np.interp(t1, rt[:, 0], rt[:, 3])
    v5 = np.convolve(np.interp(t1, gt, gv), np.ones(5) / 5, mode="same")
    diff = a_long - b_ekf - np.gradient(v5, t1)
    print("   forward acceleration minus GNSS-derived acceleration (grade at the true position):")
    for name, lo, hi in [("60 s before", ta - 60, ta), ("in the window", ta, tb), ("first 40 s", ta, ta + 40),
                         ("60 s after", tb, tb + 60)]:
        k = (t1 >= lo) & (t1 < hi)
        print(f"   {name:14s} {diff[k].mean():+.3f} m/s^2  (mean GNSS speed {3.6 * np.interp(t1[k], gt, gv).mean():3.0f} km/h)")

    err_true = default_window_trace(trace, grade_at_truth=True)[0]
    print(f"\n4. Grade looked up at the true position: EKF exit error {err:+.0f} m -> {err_true:+.0f} m")


if __name__ == "__main__":
    main()
