"""Jerk-limited speed change (A11): shared by the vehicle simulation and the scenario validation."""
import math

JERK_MPS3 = 2.0  # A11
COMFORT_ACCEL_MPS2 = 1.5  # A11


def s_curve(v0: float, v1: float, accel: float) -> tuple[float, "callable"]:
    """Jerk-limited speed change v0 -> v1 with zero acceleration at both ends: (duration, v(tau))."""
    dv = abs(v1 - v0)
    if dv == 0:
        return 0.0, lambda tau: v0
    sign = 1.0 if v1 > v0 else -1.0
    a_pk = min(accel, math.sqrt(dv * JERK_MPS3))
    t1 = a_pk / JERK_MPS3
    t2 = dv / a_pk - t1
    total = 2 * t1 + t2

    def v(tau: float) -> float:
        tau = min(tau, total)
        if tau < t1:
            d = JERK_MPS3 * tau**2 / 2
        elif tau < t1 + t2:
            d = JERK_MPS3 * t1**2 / 2 + a_pk * (tau - t1)
        else:
            d = dv - JERK_MPS3 * (total - tau) ** 2 / 2
        return v0 + sign * d

    return total, v


def s_curve_distance(v0: float, v1: float, accel: float) -> float:
    """Road length of the speed change; the S-curve is point-symmetric, so its mean speed is (v0 + v1) / 2."""
    total, _ = s_curve(v0, v1, accel)
    return (v0 + v1) / 2 * total
