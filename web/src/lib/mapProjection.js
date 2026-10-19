// World-to-screen mapping of the map view. `rot` (rad) rotates the world about the view centre; 0 = north up.

/** Rotation that turns the line from the road's first to its last point into a left-to-right line. */
export function roadRotation(map) {
  const n = map.x.length - 1
  const dx = map.x[n] - map.x[0]
  const dy = map.y[n] - map.y[0]
  return Math.hypot(dx, dy) < 1 ? 0 : -Math.atan2(dy, dx)
}

const rotate = (x, y, a) => [x * Math.cos(a) - y * Math.sin(a), x * Math.sin(a) + y * Math.cos(a)]

/** Screen pixel [px, py] (y down) of the world point (x, y). */
export function project({ cx, cy, scale, w, h, rot }, x, y) {
  const [u, v] = rotate(x - cx, y - cy, rot)
  return [w / 2 + u * scale, h / 2 - v * scale]
}

/** World offset (dx, dy) of a screen offset (px right, py down) from the view centre, at `scale`. */
export function screenToWorldOffset(px, py, scale, rot) {
  return rotate(px / scale, -py / scale, -rot)
}
