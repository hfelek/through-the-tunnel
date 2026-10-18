import { lowerBound } from './interp'

const wrapPi = (a) => a - 2 * Math.PI * Math.round(a / (2 * Math.PI))

/** x, y, heading at arc length s by interpolating the map arrays; clamps to the road. */
export function roadPointAt(map, s) {
  const n = map.s.length
  if (s <= map.s[0]) return { x: map.x[0], y: map.y[0], heading: map.heading[0] }
  if (s >= map.s[n - 1]) return { x: map.x[n - 1], y: map.y[n - 1], heading: map.heading[n - 1] }
  const i = lowerBound(map.s, s)
  const f = (s - map.s[i - 1]) / (map.s[i] - map.s[i - 1])
  return {
    x: map.x[i - 1] + f * (map.x[i] - map.x[i - 1]),
    y: map.y[i - 1] + f * (map.y[i] - map.y[i - 1]),
    heading: map.heading[i - 1] + f * wrapPi(map.heading[i] - map.heading[i - 1]),
  }
}
