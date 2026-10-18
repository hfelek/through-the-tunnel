import { memo, useMemo } from 'react'
import { estimatorColor } from '../colors'

const DISTANCES = ['500', '200', '0']
const IDEAL_CONSISTENCY_PCT = 95

const signed = (v) => `${v > 0 ? '+' : ''}${v.toFixed(1)}`
const plain = (v) => v.toFixed(1)
const absScore = (v) => Math.abs(v)
const consistencyScore = (v) => Math.abs(v - IDEAL_CONSISTENCY_PCT)

/** Columns follow the metrics present in the trace: one per tunnel and per exit / distance. */
function buildColumns(metrics) {
  const rows = Object.values(metrics)
  const tunnels = [...new Set(rows.flatMap((m) => Object.keys(m.exit_error_m ?? {})))].sort()
  const exits = [...new Set(rows.flatMap((m) => [...Object.keys(m.callout_timing_error_s ?? {}), ...(m.missed_callouts ?? []).map((c) => c.exit)]))].sort()
  const cols = [
    { key: 'rmse', label: 'In-tunnel RMSE (m)', get: (m) => m.rmse_in_tunnel_m, fmt: plain, score: absScore },
    { key: 'max', label: 'Max |error| in tunnel (m)', get: (m) => m.max_abs_error_in_tunnel_m, fmt: plain, score: absScore },
    ...tunnels.map((t) => ({ key: `exit${t}`, label: `Exit error ${t} (m)`, get: (m) => m.exit_error_m?.[t], fmt: signed, score: absScore })),
    ...tunnels.map((t) => ({ key: `rec${t}`, label: `Recovery ${t} (s)`, get: (m) => m.recovery_time_s?.[t], fmt: plain, score: absScore })),
    { key: 'jump', label: 'Max display jump (m)', get: (m) => m.max_display_jump_m, fmt: plain, score: absScore },
    { key: 'cons', label: 'Consistency (%)', get: (m) => m.consistency_pct, fmt: plain, score: consistencyScore },
  ]
  for (const e of exits) {
    for (const d of DISTANCES) {
      cols.push({
        key: `co${e}${d}`, label: `Callout ${e} @ ${d} m (s)`, fmt: signed, score: absScore,
        get: (m) => m.callout_timing_error_s?.[e]?.[d],
        missed: (m) => (m.missed_callouts ?? []).some((c) => c.exit === e && String(Math.round(c.distance_m)) === d),
      })
    }
  }
  return cols
}

/** Ids of the rows holding the best value of a column (needs at least two numeric values to mean anything). */
function bestRows(col, entries) {
  const vals = entries.flatMap(([id, m]) => (col.missed?.(m) || typeof col.get(m) !== 'number' ? [] : [[id, col.score(col.get(m))]]))
  if (vals.length < 2) return new Set()
  const best = Math.min(...vals.map((v) => v[1]))
  return new Set(vals.filter((v) => v[1] - best < 1e-9).map((v) => v[0]))
}

export default memo(function MetricsTable({ trace, estimators }) {
  const metrics = trace?.vehicles?.[0]?.metrics
  const model = useMemo(() => {
    const entries = Object.entries(metrics ?? {})
    if (!entries.length) return null
    const cols = buildColumns(metrics)
    return { entries, cols, best: Object.fromEntries(cols.map((c) => [c.key, bestRows(c, entries)])) }
  }, [metrics])

  if (!trace) return <section className="metrics empty">Run a scenario to see the metrics.</section>
  if (!model) return <section className="metrics empty">No estimator selected.</section>
  return (
    <section className="metrics">
      <table>
        <thead>
          <tr>
            <th>Method</th>
            {model.cols.map((c) => <th key={c.key}>{c.label}</th>)}
          </tr>
        </thead>
        <tbody>
          {model.entries.map(([id, m]) => (
            <tr key={id}>
              <th>
                <span className="swatch" style={{ background: estimatorColor(estimators, id) }} />
                {estimators.find((e) => e.id === id)?.label ?? id}
              </th>
              {model.cols.map((c) => {
                const v = c.get(m)
                if (c.missed?.(m)) return <td key={c.key} className="missed">missed</td>
                if (typeof v !== 'number') return <td key={c.key} className="muted">n/a</td>
                return <td key={c.key} className={model.best[c.key].has(id) ? 'best' : undefined}>{c.fmt(v)}</td>
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
})
