import { memo, useEffect, useMemo, useState } from 'react'
import { interpAt } from '../lib/interp'
import { estimatorColor, TRUTH_COLOR } from '../colors'

const HEIGHT = 160
const M = { l: 46, r: 14, t: 10, b: 24 }
const MIN_SPAN_M = 10 // flat roads still get a readable y scale
const STEP_M = 5 // drawing resolution of the profile

/** Round tick values covering [lo, hi] with about `count` ticks. */
function niceTicks(lo, hi, count) {
  const raw = (hi - lo) / count
  const mag = 10 ** Math.floor(Math.log10(raw))
  const step = [1, 2, 5, 10].map((m) => m * mag).find((s) => s >= raw)
  const ticks = []
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) ticks.push(Math.round(v / step) * step)
  return ticks
}

function makeScales(map, w) {
  const L = map.s[map.s.length - 1] - map.s[0]
  let zlo = Math.min(...map.z)
  let zhi = Math.max(...map.z)
  const span = Math.max(zhi - zlo, MIN_SPAN_M)
  const mid = (zlo + zhi) / 2
  zlo = mid - span / 2 - span * 0.05
  zhi = mid + span / 2 + span * 0.05
  const pw = w - M.l - M.r
  const ph = HEIGHT - M.t - M.b
  return {
    L, zlo, zhi,
    sx: (s) => M.l + ((s - map.s[0]) / L) * pw,
    sy: (z) => M.t + (1 - (z - zlo) / (zhi - zlo)) * ph,
  }
}

const ProfileStatic = memo(function ProfileStatic({ map, sc, w }) {
  const d = useMemo(() => {
    const n = map.s.length
    const stride = Math.max(1, Math.round(STEP_M / ((map.s[n - 1] - map.s[0]) / (n - 1))))
    const pts = []
    for (let i = 0; i < n; i += stride) pts.push(i)
    if (pts[pts.length - 1] !== n - 1) pts.push(n - 1)
    return pts.map((i, k) => `${k ? 'L' : 'M'}${sc.sx(map.s[i]).toFixed(1)} ${sc.sy(map.z[i]).toFixed(1)}`).join('')
  }, [map, sc])
  const yTicks = niceTicks(sc.zlo, sc.zhi, 4)
  const kmStep = [0.1, 0.2, 0.5, 1, 2, 5].find((k) => sc.L / 1000 / k <= 8) ?? 5
  const xTicks = []
  for (let km = 0; km * 1000 <= sc.L + 1e-6; km = Math.round((km + kmStep) * 1e6) / 1e6) xTicks.push(km)
  const yBottom = HEIGHT - M.b
  return (
    <g>
      {map.tunnels.map((t) => (
        <rect key={t.id} x={sc.sx(t.start_s)} y={M.t} width={sc.sx(t.end_s) - sc.sx(t.start_s)} height={yBottom - M.t} fill="#374151" fillOpacity={0.14} />
      ))}
      {yTicks.map((v) => (
        <g key={`y${v}`}>
          <line x1={M.l} x2={w - M.r} y1={sc.sy(v)} y2={sc.sy(v)} stroke="#e5e7eb" />
          <text x={M.l - 6} y={sc.sy(v)} className="axis-label" textAnchor="end" dominantBaseline="middle">{v}</text>
        </g>
      ))}
      {xTicks.map((km) => (
        <text key={`x${km}`} x={sc.sx(km * 1000)} y={yBottom + 14} className="axis-label" textAnchor="middle">{km}</text>
      ))}
      <path d={d} fill="none" stroke="#6b7280" strokeWidth={2} strokeLinejoin="round" />
      {map.exits.map((e) => (
        <g key={e.id}>
          <line x1={sc.sx(e.s)} x2={sc.sx(e.s)} y1={M.t} y2={yBottom} stroke="#b91c1c" strokeWidth={1.5} />
          <text x={sc.sx(e.s) + 4} y={M.t + 8} className="exit-label">{e.name ?? e.id}</text>
        </g>
      ))}
      <text x={4} y={M.t + 4} className="axis-label">z (m)</text>
      <text x={w - M.r} y={HEIGHT - 2} className="axis-label" textAnchor="end">s (km)</text>
    </g>
  )
})

/** Truth and estimate markers on the profile; the only part that depends on t. */
function ProfileMarkers({ map, sc, vehicle, estimators, t }) {
  const pos = (s) => ({ cx: sc.sx(s), cy: sc.sy(interpAt(map.s, map.z, s)) })
  const truth = vehicle.truth
  return (
    <g>
      {Object.entries(vehicle.estimates ?? {}).map(([id, e]) => (
        <circle key={id} {...pos(interpAt(e.t, e.s, t))} r={7} fill="none" stroke={estimatorColor(estimators, id)} strokeWidth={2.5} />
      ))}
      {truth?.t?.length > 0 && <circle {...pos(interpAt(truth.t, truth.s, t))} r={5} fill={TRUTH_COLOR} />}
    </g>
  )
}

export default function ElevationProfile({ trace, estimators, t }) {
  const [wrapEl, setWrapEl] = useState(null)
  const [w, setW] = useState(800)
  useEffect(() => {
    if (!wrapEl) return
    const ro = new ResizeObserver(([e]) => setW(Math.max(200, e.contentRect.width)))
    ro.observe(wrapEl)
    return () => ro.disconnect()
  }, [wrapEl])

  const map = trace?.map
  const vehicle = trace?.vehicles?.[0]
  const sc = useMemo(() => (map ? makeScales(map, w) : null), [map, w])
  return (
    <section className={`profile${map ? '' : ' empty'}`} ref={setWrapEl} style={{ height: HEIGHT }}>
      {map && vehicle ? (
        <svg width={w} height={HEIGHT}>
          <ProfileStatic map={map} sc={sc} w={w} />
          <ProfileMarkers map={map} sc={sc} vehicle={vehicle} estimators={estimators} t={t} />
        </svg>
      ) : (
        'Run a scenario to see the elevation profile.'
      )}
    </section>
  )
}
