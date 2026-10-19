"""Rotation helpers (numpy, vectorized over leading axes) shared by the sensor models and the estimators."""
import numpy as np


def skew(v: np.ndarray) -> np.ndarray:
    """Cross-product matrices (..., 3, 3) of vectors (..., 3)."""
    z = np.zeros(v.shape[:-1])
    return np.stack([z, -v[..., 2], v[..., 1], v[..., 2], z, -v[..., 0], -v[..., 1], v[..., 0], z], axis=-1).reshape(*v.shape[:-1], 3, 3)


def exp_so3(v: np.ndarray) -> np.ndarray:
    """Rotation vectors (..., 3) -> rotation matrices (..., 3, 3) (Rodrigues)."""
    th2 = np.sum(v * v, axis=-1)
    th = np.sqrt(th2)
    small = th < 1e-6
    safe = np.where(small, 1.0, th)
    a = np.where(small, 1.0 - th2 / 6.0, np.sin(safe) / safe)
    b = np.where(small, 0.5 - th2 / 24.0, (1.0 - np.cos(safe)) / safe**2)
    k = skew(v)
    return np.eye(3) + a[..., None, None] * k + b[..., None, None] * (k @ k)


def log_so3(r: np.ndarray) -> np.ndarray:
    """Rotation matrices (..., 3, 3) -> rotation vectors (..., 3); valid away from 180 deg."""
    vee = 0.5 * np.stack([r[..., 2, 1] - r[..., 1, 2], r[..., 0, 2] - r[..., 2, 0], r[..., 1, 0] - r[..., 0, 1]], axis=-1)
    s = np.linalg.norm(vee, axis=-1)
    th = np.arctan2(s, 0.5 * (np.trace(r, axis1=-2, axis2=-1) - 1.0))
    return vee * np.where(s < 1e-12, 1.0, th / np.where(s < 1e-12, 1.0, s))[..., None]


def smooth_step(x: np.ndarray) -> np.ndarray:
    """Smooth step 0..1 with zero slope at both ends."""
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)
