import { memo, useMemo, useState } from 'react'
import { Area, CartesianGrid, ComposedChart, Line, ReferenceArea, ReferenceLine, XAxis, YAxis } from 'recharts'
import ErrorBoundary from './ErrorBoundary'
import { estimatorColor, TRUTH_COLOR } from '../colors'
import { M, TICK, X_AXIS_H, X_TICK_MARGIN, Y_AXIS_W, Y_PAD, fmt, timeToX } from '../lib/plotGeometry'
import { tunnelIntervals } from '../lib/trace'

const CHART_H = 220
const TITLE_H = 18 // the title sits in a strip above the plot area, like the sensor charts
const MARGIN = { ...M, top: 36 } // room for up to three staggered label levels (x mapping is unchanged)
const LABEL_CHAR_PX = 6
const RANGES = { auto: 'Auto', 50: '±50 m', 200: '±200 m' }

/** One row per estimate time: error and the 2σ band [err - 2σ, err + 2σ] per estimator (error space). */
function buildRows(vehicle) {
  const byT = new Map()
  const ids = []
  for (const [id, est] of Object.entries(vehicle.estimates ?? {})) {
    const err = vehicle.metrics?.[id]?.error
    if (!err?.length) continue
    ids.push(id)
    const n = Math.min(err.length, est.t.length)
    for (let i = 0; i < n; i++) {
      const row = byT.get(est.t[i]) ?? { t: est.t[i] }
      row[id] = err[i]
      row[`${id}_band`] = [err[i] - 2 * est.sigma_s[i], err[i] + 2 * est.sigma_s[i]]
      byT.set(est.t[i], row)
    }
  }
  return { ids, rows: [...byT.values()].sort((a, b) => a.t - b.t) }
}

/** Own callout times per estimator, plus the ideal times (same for all estimators, taken once per distance). */
function callouts(vehicle, ids) {
  const own = ids.flatMap((id) => (vehicle.callouts?.[id] ?? []).filter((c) => c.t != null).map((c) => ({ id, t: c.t })))
  const ideal = new Map()
  for (const id of ids) {
    for (const c of vehicle.callouts?.[id] ?? []) {
      const key = `${c.exit}/${c.distance_m}`
      if (c.t_ideal != null && !ideal.has(key)) ideal.set(key, { t: c.t_ideal, label: String(c.distance_m) })
    }
  }
  return { own, ideal: [...ideal.values()] }
}

/** Stagger ideal-line labels that would overlap horizontally onto higher levels. */
function staggerLabels(ideal, duration, w) {
  const edges = []
  return [...ideal].sort((a, b) => a.t - b.t).map((c) => {
    const x = timeToX(c.t, duration, w)
    const half = (c.label.length * LABEL_CHAR_PX + 6) / 2
    let level = 0
    while (level < 2 && edges[level] !== undefined && x - half < edges[level]) level++
    edges[level] = x + half
    return { ...c, level }
  })
}

const Plot = memo(function Plot({ rows, ids, colors, own, ideal, intervals, w, duration, range }) {
  const labelled = useMemo(() => staggerLabels(ideal, duration, w), [ideal, duration, w])
  const domain = range === 'auto' ? ['auto', 'auto'] : [-range, range]
  return (
    <div className="chart-row" style={{ height: CHART_H + TITLE_H }}>
      <div className="chart-title above" style={{ height: TITLE_H }}>
        Along-track error (m), shaded: ±2σ around the estimate
        {ids.map((id) => <span key={id} style={{ color: colors[id] }}> {id}</span>)}
      </div>
      <ComposedChart width={w} height={CHART_H} data={rows} margin={MARGIN} accessibilityLayer={false}>
        <CartesianGrid vertical={false} stroke="#e5e7eb" />
        <XAxis type="number" dataKey="t" domain={[0, duration]} allowDataOverflow height={X_AXIS_H} tickMargin={X_TICK_MARGIN} tick={TICK} tickFormatter={fmt} />
        <YAxis width={Y_AXIS_W} padding={Y_PAD} domain={domain} allowDataOverflow tick={TICK} tickFormatter={fmt} tickCount={5} />
        {intervals.map((iv) => (
          <ReferenceArea key={iv.ref} x1={iv.start} x2={iv.end} fill="#374151" fillOpacity={0.14} stroke="none" ifOverflow="hidden" />
        ))}
        {ids.map((id) => (
          <Area key={`${id}_band`} dataKey={`${id}_band`} stroke="none" fill={colors[id]} fillOpacity={0.15} isAnimationActive={false} activeDot={false} connectNulls />
        ))}
        <ReferenceLine y={0} stroke="#6b7280" />
        {labelled.map((c) => (
          <ReferenceLine key={`i${c.label}`} x={c.t} stroke={TRUTH_COLOR} strokeDasharray="4 3" strokeWidth={1} ifOverflow="hidden"
            label={{ value: c.label, position: 'top', offset: 2 + c.level * 11, fontSize: 10, fill: TRUTH_COLOR }} />
        ))}
        {own.map((c, k) => <ReferenceLine key={`o${k}`} x={c.t} stroke={colors[c.id]} strokeWidth={1} ifOverflow="hidden" />)}
        {ids.map((id) => (
          <Line key={id} dataKey={id} stroke={colors[id]} strokeWidth={1.5} dot={false} isAnimationActive={false} activeDot={false} connectNulls />
        ))}
      </ComposedChart>
    </div>
  )
})

function ErrorChart({ trace, estimators, duration, w }) {
  const vehicle = trace?.vehicles?.[0]
  const [range, setRange] = useState('auto')
  const data = useMemo(() => (vehicle?.truth?.t?.length ? buildRows(vehicle) : null), [vehicle])
  const intervals = useMemo(() => tunnelIntervals(vehicle?.events, duration), [vehicle, duration])
  const marks = useMemo(() => (data ? callouts(vehicle, data.ids) : null), [vehicle, data])
  const colors = useMemo(() => Object.fromEntries((data?.ids ?? []).map((id) => [id, estimatorColor(estimators, id)])), [data, estimators])
  if (!vehicle) return null
  if (!data) return <div className="chart-controls muted">No ground truth in this trace</div>
  if (!data.ids.length) return <div className="chart-controls muted">No estimator selected</div>
  return (
    <>
      <div className="chart-controls">
        Error range:{' '}
        <select value={range} onChange={(e) => setRange(e.target.value)}>
          {Object.entries(RANGES).map(([v, label]) => <option key={v} value={v}>{label}</option>)}
        </select>
      </div>
      <ErrorBoundary name="Error chart" resetKey={data}>
        <Plot rows={data.rows} ids={data.ids} colors={colors} own={marks.own} ideal={marks.ideal} intervals={intervals}
          w={w} duration={duration} range={range === 'auto' ? 'auto' : Number(range)} />
      </ErrorBoundary>
    </>
  )
}

export default memo(ErrorChart)
