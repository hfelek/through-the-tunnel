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
// Overlay: lines and bands of all methods in one plot. Separate: one row per method, same y scale. Off: lines only (T10.6d).
const BAND_MODES = { overlay: 'Overlay', separate: 'Separate', off: 'Off' }
const ROW_H = 140 // height of one row in Separate mode

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

/** y range that holds every method's error ± 2σ: Separate rows share it, so their sizes can be compared. */
function sharedDomain(rows, ids) {
  let lo = Infinity
  let hi = -Infinity
  for (const row of rows) {
    for (const id of ids) {
      const band = row[`${id}_band`]
      if (band) { lo = Math.min(lo, band[0]); hi = Math.max(hi, band[1]) }
    }
  }
  if (!Number.isFinite(lo)) return ['auto', 'auto']
  // round outwards to a 1-2-5 step, so the axis labels are round numbers (not 98.688)
  const raw = (hi - lo || 1) / 4
  const mag = 10 ** Math.floor(Math.log10(raw))
  const step = mag * ([1, 2, 5, 10].find((m) => m * mag >= raw) ?? 10)
  return [Math.floor(lo / step) * step, Math.ceil(hi / step) * step]
}

/** `ids` are drawn as lines, `bandIds` get the ±2σ band; `domain` is the y range ([lo, hi] or auto). */
const Plot = memo(function Plot({ rows, ids, bandIds, title, height, margin, colors, own, ideal, intervals, w, duration, domain }) {
  const labelled = useMemo(() => staggerLabels(ideal, duration, w), [ideal, duration, w])
  return (
    <div className="chart-row">
      <div className="chart-title above" style={{ height: TITLE_H }}>
        {title}
        {ids.length > 1 && ids.map((id) => <span key={id} style={{ color: colors[id] }}> {id}</span>)}
      </div>
      <ComposedChart width={w} height={height} data={rows} margin={margin} accessibilityLayer={false}>
        <CartesianGrid vertical={false} stroke="#e5e7eb" />
        <XAxis type="number" dataKey="t" domain={[0, duration]} allowDataOverflow height={X_AXIS_H} tickMargin={X_TICK_MARGIN} tick={TICK} tickFormatter={fmt} />
        <YAxis width={Y_AXIS_W} padding={Y_PAD} domain={domain} allowDataOverflow tick={TICK} tickFormatter={fmt} tickCount={5} />
        {intervals.map((iv) => (
          <ReferenceArea key={iv.ref} x1={iv.start} x2={iv.end} fill="#374151" fillOpacity={0.14} stroke="none" ifOverflow="hidden" />
        ))}
        {bandIds.map((id) => (
          <Area key={`${id}_band`} dataKey={`${id}_band`} stroke="none" fill={colors[id]} fillOpacity={0.15} isAnimationActive={false} activeDot={false} connectNulls />
        ))}
        <ReferenceLine y={0} stroke="#6b7280" />
        {labelled.map((c) => (
          <ReferenceLine key={`i${c.label}`} x={c.t} stroke={TRUTH_COLOR} strokeDasharray="4 3" strokeWidth={1} ifOverflow="hidden"
            label={{ value: c.label, position: 'top', offset: 2 + c.level * 11, fontSize: 10, fill: TRUTH_COLOR }} />
        ))}
        {own.filter((c) => ids.includes(c.id)).map((c, k) => <ReferenceLine key={`o${k}`} x={c.t} stroke={colors[c.id]} strokeWidth={1} ifOverflow="hidden" />)}
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
  const [bands, setBands] = useState('overlay')
  const data = useMemo(() => (vehicle?.truth?.t?.length ? buildRows(vehicle) : null), [vehicle])
  const intervals = useMemo(() => tunnelIntervals(vehicle?.events, duration), [vehicle, duration])
  const marks = useMemo(() => (data ? callouts(vehicle, data.ids) : null), [vehicle, data])
  const colors = useMemo(() => Object.fromEntries((data?.ids ?? []).map((id) => [id, estimatorColor(estimators, id)])), [data, estimators])
  if (!vehicle) return null
  if (!data) return <div className="chart-controls muted">No ground truth in this trace</div>
  if (!data.ids.length) return <div className="chart-controls muted">No estimator selected</div>
  const separate = bands === 'separate' && data.ids.length > 1 // one method: nothing to separate
  const fixed = range === 'auto' ? null : [-Number(range), Number(range)]
  // Auto: Recharts picks the range, except in Separate where one range must serve all rows
  const domain = fixed ?? (separate ? sharedDomain(data.rows, data.ids) : ['auto', 'auto'])
  const common = { rows: data.rows, colors, ideal: marks.ideal, intervals, w, duration, domain }
  return (
    <>
      <div className="chart-controls">
        Error range:{' '}
        <select value={range} onChange={(e) => setRange(e.target.value)}>
          {Object.entries(RANGES).map(([v, label]) => <option key={v} value={v}>{label}</option>)}
        </select>
        {' '}Bands:{' '}
        <select value={bands} onChange={(e) => setBands(e.target.value)}>
          {Object.entries(BAND_MODES).map(([v, label]) => <option key={v} value={v}>{label}</option>)}
        </select>
      </div>
      <ErrorBoundary name="Error chart" resetKey={data}>
        {separate ? data.ids.map((id) => (
          <Plot key={id} {...common} ids={[id]} bandIds={[id]} own={marks.own} height={ROW_H}
            margin={{ ...MARGIN, top: marks.ideal.length ? MARGIN.top : 12 }} // callout labels need the room above the plot
            title={`${estimators.find((e) => e.id === id)?.label ?? id}: along-track error (m), shaded ±2σ`} />
        )) : (
          <Plot {...common} ids={data.ids} bandIds={bands === 'off' ? [] : data.ids} own={marks.own} height={CHART_H} margin={MARGIN}
            title={bands === 'off' ? 'Along-track error (m)' : 'Along-track error (m), shaded: ±2σ around the estimate'} />
        )}
      </ErrorBoundary>
    </>
  )
}

export default memo(ErrorChart)
