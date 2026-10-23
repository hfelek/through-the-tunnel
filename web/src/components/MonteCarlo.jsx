import { memo, useMemo, useState } from 'react'
import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, XAxis, YAxis, ZAxis } from 'recharts'
import InfoModal from './InfoModal'
import { monteCarlo } from '../api'
import { estimatorColor } from '../colors'

const FLOOR_M = 0.1 // |error| below this is drawn at this value, like the overview plot of the full study
const INFO = 'One dot per seed: the absolute tunnel exit error of a small Monte Carlo run on the scenario and the settings '
  + 'currently in the panel (the dash is the median). A seed changes all random draws (sensor noise, GNSS, beacons, '
  + 'the particle filter) but not the scenario. The y axis is logarithmic. The table gives the median and p90 of the '
  + 'absolute exit error and the mean consistency. Run again after a change to see the new spread. '
  + 'The full study (all scenarios, 50 seeds) is `make montecarlo`.'

const jitter = (k) => ((k * 0.6180339887) % 1 - 0.5) * 0.5 // deterministic spread of the dots across the column
const fmt = (v) => (typeof v === 'number' ? v.toFixed(1) : 'n/a')

/** Powers of ten from FLOOR_M up to the first one above the largest value. */
function logTicks(max) {
  const ticks = [FLOOR_M]
  while (ticks[ticks.length - 1] < max) ticks.push(ticks[ticks.length - 1] * 10)
  return ticks
}

function Strip({ ids, estimators, data, tunnel }) {
  const series = ids.map((id, i) => {
    const errs = data.estimators[id].exit_error_m[tunnel] ?? []
    return {
      id, i,
      dots: errs.map((v, k) => ({ x: i + jitter(k), y: Math.max(Math.abs(v), FLOOR_M) })),
      median: [{ x: i, y: Math.max(data.estimators[id].median_abs_exit_error_m[tunnel] ?? FLOOR_M, FLOOR_M) }],
    }
  })
  const max = Math.max(FLOOR_M, ...series.flatMap((s) => s.dots.map((d) => d.y)))
  const ticks = logTicks(max)
  const dash = (color) => ({ cx, cy }) => <line x1={cx - 22} x2={cx + 22} y1={cy} y2={cy} stroke={color} strokeWidth={3} />
  return (
    <ResponsiveContainer width="100%" height={260}>
      <ScatterChart margin={{ top: 8, right: 16, bottom: 4, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis type="number" dataKey="x" domain={[-0.5, ids.length - 0.5]} ticks={ids.map((_, i) => i)} interval={0}
          tickFormatter={(i) => estimators.find((e) => e.id === ids[i])?.label ?? ids[i]} />
        <YAxis type="number" dataKey="y" scale="log" domain={[FLOOR_M, ticks[ticks.length - 1]]} ticks={ticks} allowDataOverflow
          width={64} tickFormatter={(v) => String(+v.toPrecision(2))}
          label={{ value: `|exit error| (m), log, clipped at ${FLOOR_M} m`, angle: -90, position: 'insideLeft', style: { textAnchor: 'middle', fontSize: 12 } }} />
        <ZAxis range={[36, 36]} />
        {series.map((s) => (
          <Scatter key={s.id} data={s.dots} fill={estimatorColor(estimators, s.id)} fillOpacity={0.55} isAnimationActive={false} />
        ))}
        {series.map((s) => (
          <Scatter key={`${s.id}-median`} data={s.median} shape={dash(estimatorColor(estimators, s.id))} isAnimationActive={false} />
        ))}
      </ScatterChart>
    </ResponsiveContainer>
  )
}

function Stats({ ids, estimators, data, tunnel }) {
  return (
    <table>
      <thead>
        <tr><th>Estimator</th><th>Median |exit error| (m)</th><th>p90 |exit error| (m)</th><th>Mean consistency (%)</th></tr>
      </thead>
      <tbody>
        {ids.map((id) => {
          const e = data.estimators[id]
          return (
            <tr key={id}>
              <th><span className="swatch" style={{ background: estimatorColor(estimators, id) }} /> {estimators.find((x) => x.id === id)?.label ?? id}</th>
              <td>{fmt(e.median_abs_exit_error_m[tunnel])}</td>
              <td>{fmt(e.p90_abs_exit_error_m[tunnel])}</td>
              <td>{fmt(e.mean_consistency_pct)}</td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

/** Monte Carlo on the scenario and parameters currently in the panel (POST /api/montecarlo). */
export default memo(function MonteCarlo({ scenario, estimators, params }) {
  const [nSeeds, setNSeeds] = useState(20)
  const [picked, setPicked] = useState(null) // null = the default selection
  const [result, setResult] = useState(null) // { data, scenario, ids }
  const [running, setRunning] = useState(false)
  const [error, setError] = useState(null)
  const [tunnel, setTunnel] = useState(null)
  const [info, setInfo] = useState(false)

  const on = picked ?? estimators.filter((e) => e.mc_default).map((e) => e.id)
  const toggle = (id) => setPicked(estimators.map((e) => e.id).filter((x) => (x === id ? !on.includes(x) : on.includes(x))))
  const seeds = Math.min(50, Math.max(1, Math.round(nSeeds) || 1))

  const run = () => {
    setRunning(true)
    setError(null)
    const chosen = Object.fromEntries(on.map((id) => [id, params[id] ?? {}]))
    monteCarlo(scenario, chosen, seeds).then(
      (data) => { setResult({ data, scenario, ids: on }); setTunnel(null); setRunning(false) },
      (e) => { setError(e.message); setRunning(false) },
    )
  }

  const shownTunnel = tunnel ?? result?.data.tunnels[0]
  const outdated = result && result.scenario !== scenario
  const body = useMemo(() => result && shownTunnel && (
    <>
      <Strip ids={result.ids} estimators={estimators} data={result.data} tunnel={shownTunnel} />
      <Stats ids={result.ids} estimators={estimators} data={result.data} tunnel={shownTunnel} />
    </>
  ), [result, shownTunnel, estimators])

  return (
    <section className="mc">
      <div className="mc-head">
        <h3>Monte Carlo</h3>
        <button className="secondary info-i" title="About this panel" aria-label="About the Monte Carlo panel" onClick={() => setInfo(true)}>i</button>
        <label>Seeds <input type="number" min={1} max={50} value={nSeeds} onChange={(e) => setNSeeds(e.target.value)} style={{ width: 56 }} /></label>
        {estimators.map((e) => (
          <label key={e.id}><input type="checkbox" checked={on.includes(e.id)} onChange={() => toggle(e.id)} /> {e.label}</label>
        ))}
        <button onClick={run} disabled={running || !scenario || on.length === 0}>Run Monte Carlo</button>
        {running && <span className="loading"><span className="spinner" /> Running {seeds} seeds…</span>}
        {result && result.data.tunnels.length > 1 && (
          <label>Tunnel <select value={shownTunnel} onChange={(e) => setTunnel(e.target.value)}>
            {result.data.tunnels.map((t) => <option key={t} value={t}>{t}</option>)}
          </select></label>
        )}
      </div>
      {error && <div className="error-box">{error}</div>}
      {outdated && <div className="outdated">Outdated: the scenario changed since this run</div>}
      {result && !shownTunnel && <p className="muted">This scenario has no tunnel exit to measure.</p>}
      {body}
      {result && <p className="muted">{result.data.n_seeds} seeds, {result.data.seconds} s.</p>}
      {info && <InfoModal title="Monte Carlo" text={INFO} onClose={() => setInfo(false)} />}
    </section>
  )
})
