"""Stationary detector (T8.3, A32): is the phone, and so the car, standing still? Raw IMU only, no alignment needed."""
from __future__ import annotations

import math
from collections import deque

WINDOW_S = 1.0  # sliding window for the standard deviations
HOLD_S = 0.5  # both must stay low this long before "stationary" is reported


class StationaryDetector:
    """Stationary when the std of |accelerometer| and of |gyro| over the last second stay below their limits for 0.5 s.

    The magnitude does not depend on how the phone is mounted. Hand motion and driving vibration keep the std high.
    """

    def __init__(self, acc_std: float, gyro_std: float) -> None:
        self.acc_std, self.gyro_std = acc_std, gyro_std
        self._window: deque[tuple[float, float, float]] = deque()  # (t, |a|, |g|)
        self._sums = [0.0, 0.0, 0.0, 0.0]  # sum |a|, sum |a|^2, sum |g|, sum |g|^2 over the window
        self._quiet_since: float | None = None

    @staticmethod
    def _std(total: float, total_sq: float, n: int) -> float:
        return math.sqrt(max(total_sq / n - (total / n) ** 2, 0.0))  # max(): rounding can make it slightly negative

    def update(self, t: float, ax: float, ay: float, az: float, gx: float, gy: float, gz: float) -> bool:
        """Feed one IMU sample (time order); returns whether the vehicle is stationary now."""
        a, g = math.sqrt(ax * ax + ay * ay + az * az), math.sqrt(gx * gx + gy * gy + gz * gz)
        self._window.append((t, a, g))
        for k, v in enumerate((a, a * a, g, g * g)):
            self._sums[k] += v
        while self._window[0][0] < t - WINDOW_S:  # drop samples older than the window
            _, old_a, old_g = self._window.popleft()
            for k, v in enumerate((old_a, old_a * old_a, old_g, old_g * old_g)):
                self._sums[k] -= v
        if t - self._window[0][0] < 0.9 * WINDOW_S:  # window not full yet (start of the run)
            self._quiet_since = None
            return False
        n = len(self._window)
        quiet = (self._std(self._sums[0], self._sums[1], n) < self.acc_std
                 and self._std(self._sums[2], self._sums[3], n) < self.gyro_std)
        if not quiet:  # leave as soon as either limit is exceeded
            self._quiet_since = None
            return False
        if self._quiet_since is None:
            self._quiet_since = t
        return t - self._quiet_since >= HOLD_S
