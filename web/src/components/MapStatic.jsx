import { memo, useMemo } from 'react'
import { lowerBound } from '../lib/interp'
import { roadPointAt } from '../lib/road'

const STEP_M = 5 // drawing resolution of the centerline

/** SVG path through map points with s in [s0, s1], thinned to about STEP_M. */
function pathD(map, s0, s1) {
  const n = map.s.length
  const ds = (map.s[n - 1] - map.s[0]) / (n - 1)
  const stride = Math.max(1, Math.round(STEP_M / ds))
  const a = lowerBound(map.s, s0)
  const b = Math.min(n - 1, lowerBound(map.s, s1))
  const pts = []
  for (let i = a; i < b; i += stride) pts.push([map.x[i], map.y[i]])
  pts.push([map.x[b], map.y[b]])
  return pts.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`).join('')
}

/** Centerline and tunnel paths in world coordinates; the parent applies the view transform, so this never re-renders on pan, zoom or t. */
export const RoadPaths = memo(function RoadPaths({ map }) {
  const road = useMemo(() => pathD(map, map.s[0], map.s[map.s.length - 1]), [map])
  const tunnels = useMemo(() => map.tunnels.map((t) => ({ id: t.id, d: pathD(map, t.start_s, t.end_s) })), [map])
  return (
    <>
      <path d={road} stroke="#9ca3af" strokeWidth={3} vectorEffect="non-scaling-stroke" />
      {tunnels.map((t) => (
        <path key={t.id} d={t.d} stroke="#374151" strokeWidth={8} vectorEffect="non-scaling-stroke" />
      ))}
    </>
  )
})

/** Exit ticks and names in screen coordinates, so text and ticks never scale with zoom. */
export const ExitLayer = memo(function ExitLayer({ map, cx, cy, scale, w, h }) {
  return (
    <g>
      {map.exits.map((e) => {
        const p = roadPointAt(map, e.s)
        const a = roadPointAt(map, e.s - 2)
        const b = roadPointAt(map, e.s + 2)
        const px = w / 2 + (p.x - cx) * scale
        const py = h / 2 - (p.y - cy) * scale
        // screen-space unit normal to the road tangent (y is flipped)
        const tx = b.x - a.x
        const ty = -(b.y - a.y)
        const len = Math.hypot(tx, ty) || 1
        const nx = -ty / len
        const ny = tx / len
        return (
          <g key={e.id}>
            <line x1={px - nx * 10} y1={py - ny * 10} x2={px + nx * 10} y2={py + ny * 10} stroke="#b91c1c" strokeWidth={2.5} />
            <text x={px + nx * 14} y={py + ny * 14} className="exit-label" dominantBaseline="middle" textAnchor={nx < -0.3 ? 'end' : nx > 0.3 ? 'start' : 'middle'}>
              {e.name ?? e.id}
            </text>
          </g>
        )
      })}
    </g>
  )
})
