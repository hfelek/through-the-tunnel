import { memo, useMemo, useState } from 'react'
import { CartesianGrid, Line, LineChart, ReferenceArea, Scatter, ScatterChart, XAxis, YAxis, ZAxis } from 'recharts'
import ErrorBoundary from './ErrorBoundary'
import { buildCharts } from '../lib/sensorSeries'
import { M, TICK, X_AXIS_H, Y_AXIS_W, fmt } from '../lib/plotGeometry'
import { tunnelIntervals } from '../lib/trace'

const CHART_H = 120

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

/** All rows; memoized so a playback tick never re-renders Recharts. */
const Rows = memo(function Rows({ charts, shown, w, duration, intervals }) {
  return charts.filter((c) => shown[c.id]).map((c) => (
    <ErrorBoundary key={c.id} name={c.title} resetKey={c.data ?? c.series}>
      <ChartRow spec={c} w={w} duration={duration} intervals={intervals} />
    </ErrorBoundary>
  ))
})

function SensorCharts({ trace, duration, w }) {
  const vehicle = trace?.vehicles?.[0]
  const charts = useMemo(() => buildCharts(vehicle), [vehicle])
  const intervals = useMemo(() => tunnelIntervals(vehicle?.events, duration), [vehicle, duration])
  const [hidden, setHidden] = useState({})
  const shown = useMemo(() => Object.fromEntries(charts.map((c) => [c.id, !hidden[c.id]])), [charts, hidden])
  if (!vehicle) return null
  return (
    <>
      <div className="chart-controls chart-toggles">
        {charts.map((c) => (
          <label key={c.id}>
            <input type="checkbox" checked={shown[c.id]} onChange={() => setHidden((h) => ({ ...h, [c.id]: !h[c.id] }))} /> {c.title.split(' (')[0]}
          </label>
        ))}
      </div>
      <Rows charts={charts} shown={shown} w={w} duration={duration} intervals={intervals} />
    </>
  )
}

export default memo(SensorCharts)
