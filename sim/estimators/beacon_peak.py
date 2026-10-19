"""Beacon pass detector (T8.5, A33): finds the moment the car is closest to one beacon from its RSSI packets."""
from __future__ import annotations

from collections import deque

SMOOTH_S = 1.0  # moving-average window (A33)
SILENCE_S = 1.0  # a beacon not heard for this long has been passed (A33)
PLATEAU_DB = 1.0  # smoothed RSSI within this of its maximum counts as "still near the peak" (A33)
PLATEAU_S = 3.0  # a plateau longer than this means the car stopped next to the beacon (A33)


class PeakDetector:
    """One per beacon. `add` takes a packet, `poll` takes the clock; both return t_peak when a pass has just ended."""

    def __init__(self, min_dbm: float, drop_db: float) -> None:
        self.min_dbm, self.drop_db = min_dbm, drop_db
        self._packets: deque[tuple[float, float]] = deque()  # (t, rssi) of the last second
        self._sum = 0.0
        self._pass: list[tuple[float, float]] = []  # (t, smoothed rssi) since the smoothed value first passed min_dbm
        self._armed = True  # False after a detection until the signal has faded below min_dbm
        self._t_heard = 0.0

    def add(self, t: float, rssi: float) -> float | None:
        self._t_heard = t
        self._packets.append((t, rssi))
        self._sum += rssi
        while self._packets[0][0] < t - SMOOTH_S:  # the average covers the last second only
            self._sum -= self._packets.popleft()[1]
        smooth = self._sum / len(self._packets)
        if smooth < self.min_dbm:
            self._pass, self._armed = [], True  # too weak: not a pass, and the next one may start
            return None
        if not self._armed:
            return None  # still on the tail of a pass that was already reported
        self._pass.append((t, smooth))
        peak = max(p for _, p in self._pass)
        return self._finish() if smooth <= peak - self.drop_db else None

    def poll(self, t: float) -> float | None:
        """Silence rule: the pass ended if a pass is open and nothing was heard for SILENCE_S."""
        if self._pass and t - self._t_heard >= SILENCE_S:
            return self._finish()
        return None

    def _finish(self) -> float:
        peak = max(p for _, p in self._pass)
        near = [t for t, p in self._pass if p >= peak - PLATEAU_DB]  # times when the car was within 1 dB of the peak
        t_peak = max(self._pass, key=lambda tp: tp[1])[0]
        if near[-1] - near[0] > PLATEAU_S:
            t_peak = 0.5 * (near[0] + near[-1])  # stopped next to the beacon: the middle of the plateau
        self._pass, self._armed = [], False
        self._packets.clear()
        self._sum = 0.0
        return t_peak
