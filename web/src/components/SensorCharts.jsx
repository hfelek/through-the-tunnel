import { memo, useCallback, useEffect, useMemo, useState } from 'react'
import { CartesianGrid, Line, LineChart, ReferenceArea, Scatter, ScatterChart, XAxis, YAxis, ZAxis } from 'recharts'
import ErrorBoundary from './ErrorBoundary'
import { buildCharts } from '../lib/sensorSeries'
import { tunnelIntervals } from '../lib/trace'

const CHART_H = 120
// Shared plot geometry: every chart and the cursor overlay use these, so x maps identically.
const Y_AXIS_W = 46
const M = { top: 6, right: 14, bottom: 0, left: 0 }
const X_AXIS_H = 18
const TICK = { fontSize: 11, fill: '#6b7280' }
const fmt = (v) => Number(v.toPrecision(5))

const ChartRow = memo(function ChartRow({ spec, w, duration, intervals }) {
  const x = <XAxis type="number" dataKey="t" domain={[0, duration]} allowDataOverflow height={X_AXIS_H} tick={TICK} tickFormatter={fmt} />
  const y = <YAxis width={Y_AXIS_W} domain={['auto', 'auto']} tick={TICK} tickFormatter={fmt} tickCount={4} {...(spec.type === 'scatter' ? { dataKey: 'rssi' } : {})} />
  const shade = intervals.map((iv) => (
    <ReferenceArea key={iv.ref} x1={iv.start} x2={iv.end} fill="#374151" fillOpacity={0.14} stroke="none" ifOverflow="hidden" />
  ))
  const grid = <CartesianGrid vertical={false} stroke="#e5e7eb" />
  return (
    <div className="chart-row" style={{ height: CHART_H }}>
      <div className="chart-title">
        {spec.title} ({spec.unit})
        {spec.type === 'line' && spec.series.length > 1 &&
          spec.series.map((s) => <span key={s.key} style={{ color: s.color }}> {s.key}</span>)}
      </div>
      {spec.type === 'line' ? (
        <LineChart width={w} height={CHART_H} data={spec.data} margin={M} accessibilityLayer={false}>
          {grid}{x}{y}{shade}
          {spec.series.map((s) => (
            <Line key={s.key} dataKey={s.key} stroke={s.color} strokeWidth={1.2} dot={false} isAnimationActive={false} connectNulls={false} />
          ))}
        </LineChart>
      ) : (
        <ScatterChart width={w} height={CHART_H} margin={M} accessibilityLayer={false}>
          {grid}{x}{y}<ZAxis range={[6, 6]} />{shade}
          {spec.series.map((s) => (
            <Scatter key={s.key} name={s.key} data={s.data} fill={s.color} isAnimationActive={false} />
          ))}
        </ScatterChart>
      )}
    </div>
  )
})

/** All charts; memoized so a playback tick never re-renders Recharts. */
const ChartStack = memo(function ChartStack({ charts, shown, w, duration, intervals }) {
  return charts.filter((c) => shown[c.id]).map((c) => (
    <ErrorBoundary key={c.id} name={c.title} resetKey={c.data ?? c.series}>
      <ChartRow spec={c} w={w} duration={duration} intervals={intervals} />
    </ErrorBoundary>
  ))
})

export default function SensorCharts({ trace, duration, t, onSeek }) {
  const vehicle = trace?.vehicles?.[0]
  const charts = useMemo(() => buildCharts(vehicle), [vehicle])
  const intervals = useMemo(() => tunnelIntervals(vehicle?.events, duration), [vehicle, duration])
  const [hidden, setHidden] = useState({})
  const shown = useMemo(() => Object.fromEntries(charts.map((c) => [c.id, !hidden[c.id]])), [charts, hidden])

  const [wrapEl, setWrapEl] = useState(null)
  const [w, setW] = useState(800)
  useEffect(() => {
    if (!wrapEl) return
    const ro = new ResizeObserver(([e]) => setW(Math.max(200, Math.round(e.contentRect.width))))
    ro.observe(wrapEl)
    return () => ro.disconnect()
  }, [wrapEl])

  const plotW = w - Y_AXIS_W - M.right
  const onClick = useCallback((e) => {
    if (!duration) return
    const r = e.currentTarget.getBoundingClientRect()
    const f = (e.clientX - r.left - Y_AXIS_W - M.left) / (r.width - Y_AXIS_W - M.left - M.right)
    onSeek(Math.min(Math.max(f, 0), 1) * duration)
  }, [duration, onSeek])

  if (!vehicle || !duration) return <section className="charts empty">Run a scenario to see the sensor charts.</section>
  const anyShown = charts.some((c) => shown[c.id])
  return (
    <section className="charts">
      <div className="chart-toggles">
        {charts.map((c) => (
          <label key={c.id}>
            <input type="checkbox" checked={shown[c.id]} onChange={() => setHidden((h) => ({ ...h, [c.id]: !h[c.id] }))} /> {c.title.split(' (')[0]}
          </label>
        ))}
      </div>
      <div className="chart-stack" ref={setWrapEl} onClick={onClick}>
        <ChartStack charts={charts} shown={shown} w={w} duration={duration} intervals={intervals} />
        {anyShown && <div className="chart-cursor" style={{ left: Y_AXIS_W + M.left + (t / duration) * plotW }} />}
      </div>
    </section>
  )
}
