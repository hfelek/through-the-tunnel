"""Road geometry and map matching (docs/CONTRACTS.md section 3.1: ENU, arc length s)."""
from dataclasses import dataclass

import numpy as np

from sim.contracts.scenario import Arc, Exit, Road, SpeedLimit, Tunnel

RESOLUTION_M = 1.0


@dataclass
class Centerline:
    """Centerline sampled at ~1 m; heading is ENU (rad, CCW from east), grade is rise/run."""

    s: np.ndarray
    x: np.ndarray
    y: np.ndarray
    z: np.ndarray
    heading: np.ndarray
    curvature: np.ndarray
    grade: np.ndarray


def build_centerline(road: Road, step_m: float = RESOLUTION_M) -> Centerline:
    """Integrate segments exactly (lines and circular arcs); left turn = positive curvature."""
    s_parts, x_parts, y_parts, z_parts, h_parts, k_parts, g_parts = ([] for _ in range(7))
    x0 = y0 = z0 = s0 = 0.0
    h0 = np.deg2rad(road.start_heading_deg)
    for seg in road.segments:
        n = max(int(np.ceil(seg.length_m / step_m)), 1)
        d = np.linspace(0.0, seg.length_m, n + 1)
        k = 0.0
        if isinstance(seg, Arc):
            k = (1.0 if seg.turn == "left" else -1.0) / seg.radius_m
        h = h0 + k * d
        if k == 0.0:
            x, y = x0 + d * np.cos(h0), y0 + d * np.sin(h0)
        else:
            x = x0 + (np.sin(h) - np.sin(h0)) / k
            y = y0 - (np.cos(h) - np.cos(h0)) / k
        g = seg.grade_pct / 100.0
        z = z0 + g * d
        s_parts.append(s0 + d)
        x_parts.append(x)
        y_parts.append(y)
        z_parts.append(z)
        h_parts.append(h)
        k_parts.append(np.full_like(d, k))
        g_parts.append(np.full_like(d, g))
        s0, x0, y0, z0, h0 = s0 + seg.length_m, x[-1], y[-1], z[-1], h[-1]

    def cat(parts: list[np.ndarray]) -> np.ndarray:
        # drop each segment's first point after the first (duplicate of previous end)
        return np.concatenate([parts[0]] + [p[1:] for p in parts[1:]])

    cl = Centerline(*(cat(p) for p in (s_parts, x_parts, y_parts, z_parts, h_parts, k_parts, g_parts)))
    return _fix_joints(cl, k_parts, g_parts)


def _fix_joints(cl: Centerline, k_parts: list[np.ndarray], g_parts: list[np.ndarray]) -> Centerline:
    """Samples at a joint take the curvature and grade of the segment that starts there."""
    idx = 0
    for kp, gp in zip(k_parts[:-1], g_parts[:-1]):
        idx += len(kp) - 1
        # the joint sample was dropped from the next segment, so use its next-sample values
        cl.curvature[idx] = cl.curvature[idx + 1]
        cl.grade[idx] = cl.grade[idx + 1]
    return cl


class RoadMap:
    """Road geometry queries: at(s), project(x, y), in_tunnel(s)."""

    def __init__(self, road: Road, step_m: float = RESOLUTION_M) -> None:
        self.road = road
        self.line = build_centerline(road, step_m)
        self.length_m = float(self.line.s[-1])
        self.tunnels: list[Tunnel] = road.tunnels
        self.exits: list[Exit] = road.exits
        self.speed_limits: list[SpeedLimit] = road.speed_limits

    def at(self, s: float | np.ndarray) -> dict[str, np.ndarray]:
        """Interpolate x, y, z, heading, curvature, grade at arc length s (clamped to the road)."""
        c = self.line
        s = np.clip(np.asarray(s, dtype=float), 0.0, self.length_m)
        out = {n: np.interp(s, c.s, getattr(c, n)) for n in ("x", "y", "z", "heading")}
        # curvature and grade are piecewise constant: take the sample at or before s
        i = np.clip(np.searchsorted(c.s, s, side="right") - 1, 0, len(c.s) - 1)
        out["curvature"] = c.curvature[i]
        out["grade"] = c.grade[i]
        return out

    def project(self, x: float | np.ndarray, y: float | np.ndarray) -> np.ndarray:
        """Map-match (x, y) to the nearest point of the centerline; returns s."""
        c = self.line
        x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
        j = np.argmin((c.x[None, :] - x.reshape(-1, 1)) ** 2 + (c.y[None, :] - y.reshape(-1, 1)) ** 2, axis=1)
        best_s = c.s[j].copy()
        best_d = np.full(j.shape, np.inf)
        for a in (np.clip(j - 1, 0, len(c.s) - 2), np.clip(j, 0, len(c.s) - 2)):
            px, py = c.x[a], c.y[a]
            vx, vy = c.x[a + 1] - px, c.y[a + 1] - py
            t = np.clip(((x.ravel() - px) * vx + (y.ravel() - py) * vy) / (vx * vx + vy * vy), 0.0, 1.0)
            d = np.hypot(px + t * vx - x.ravel(), py + t * vy - y.ravel())
            better = d < best_d
            best_d = np.where(better, d, best_d)
            best_s = np.where(better, c.s[a] + t * (c.s[a + 1] - c.s[a]), best_s)
        return best_s.reshape(x.shape)

    def in_tunnel(self, s: float | np.ndarray) -> np.ndarray:
        """True where s lies inside any tunnel."""
        s = np.asarray(s, dtype=float)
        inside = np.zeros(s.shape, dtype=bool)
        for t in self.tunnels:
            inside |= (s >= t.start_s) & (s <= t.end_s)
        return inside
