import { lowerBound, interpAt } from '../lib/interp'
import { roadPointAt } from '../lib/road'
import { estimateAt } from '../lib/trace'
import { estimatorColor, TRUTH_COLOR } from '../colors'

const GNSS_WINDOW_S = 10
const MIN_BAR_PX = 3 // display-only: keeps a tiny 2*sigma bar visible; not a data value
const BAR_SAMPLES = 24

/** Truth, estimates, ±2σ bars and recent GNSS fixes; the only map layer that depends on t. */
export default function MapDynamic({ map, vehicle, estimators, t, cx, cy, scale, w, h }) {
  const sx = (x) => w / 2 + (x - cx) * scale
  const sy = (y) => h / 2 - (y - cy) * scale
  const road0 = map.s[0]
  const road1 = map.s[map.s.length - 1]
  const truth = vehicle.truth
  const sTrue = truth?.t?.length ? interpAt(truth.t, truth.s, t) : null

  const bar = (s, sigma) => {
    const half = Math.max(2 * sigma, MIN_BAR_PX / 2 / scale)
    const a = Math.max(road0, s - half)
    const b = Math.min(road1, s + half)
    const pts = []
    for (let k = 0; k <= BAR_SAMPLES; k++) {
      const p = roadPointAt(map, a + ((b - a) * k) / BAR_SAMPLES)
      pts.push(`${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`)
    }
    return pts.join(' ')
  }

  const gnss = vehicle.measurements?.gnss
  const dots = []
  if (gnss?.t?.length) {
    const end = lowerBound(gnss.t, t + 1e-9)
    for (let i = lowerBound(gnss.t, t - GNSS_WINDOW_S); i < end; i++) {
      dots.push(<circle key={i} cx={sx(gnss.x[i])} cy={sy(gnss.y[i])} r={2.5} fill="#6b7280" fillOpacity={0.6} />)
    }
  }

  const est = Object.entries(vehicle.estimates ?? {}).map(([id, e]) => {
    const { s, shown, held } = estimateAt(e, t)
    const sigma = interpAt(e.t, e.sigma_s, t)
    const p = roadPointAt(map, shown) // the marker is the displayed position; the bar stays centred on s
    const raw = held ? roadPointAt(map, s) : null
    const color = estimatorColor(estimators, id)
    return { id, color, s, sigma, p, raw }
  })

  return (
    <g>
      {dots}
      {est.map((e) => (
        <polyline key={`bar-${e.id}`} points={bar(e.s, e.sigma)} fill="none" stroke={e.color} strokeOpacity={0.35} strokeWidth={8} strokeLinecap="butt" strokeLinejoin="round" />
      ))}
      {sTrue != null && (() => {
        const p = roadPointAt(map, sTrue)
        return <circle cx={sx(p.x)} cy={sy(p.y)} r={6} fill={TRUTH_COLOR} />
      })()}
      {est.map((e) => e.raw && (
        <circle key={`raw-${e.id}`} cx={sx(e.raw.x)} cy={sy(e.raw.y)} r={9} fill="none" stroke={e.color} strokeOpacity={0.6} strokeWidth={1} />
      ))}
      {est.map((e) => (
        <circle key={e.id} cx={sx(e.p.x)} cy={sy(e.p.y)} r={9} fill="none" stroke={e.color} strokeWidth={2.5} />
      ))}
    </g>
  )
}
