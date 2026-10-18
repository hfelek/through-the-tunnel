import { estimatorColor, TRUTH_COLOR } from '../colors'

const fmt = (v, unit) => (typeof v === 'number' ? `${v.toFixed(1)} ${unit}` : 'n/a')

function duration(vehicle) {
  const t = vehicle.truth?.t?.length
    ? vehicle.truth.t
    : Object.values(vehicle.estimates ?? {})[0]?.t
  return t?.length ? t[t.length - 1] : null
}

export default function Panel({ trace, estimators }) {
  const vehicle = trace?.vehicles?.[0]
  if (!vehicle) return <aside className="panel"><p className="muted">Run a scenario to see results.</p></aside>
  const dur = duration(vehicle)
  return (
    <aside className="panel">
      <h2>
        <span className="swatch" style={{ background: TRUTH_COLOR }} />
        {vehicle.id}
      </h2>
      <p>Simulated duration: <b>{fmt(dur, 's')}</b></p>
      {Object.entries(vehicle.metrics ?? {}).map(([id, m]) => {
        const label = estimators.find((e) => e.id === id)?.label ?? id
        const exits = Object.entries(m.exit_error_m ?? {})
        return (
          <section key={id} className="est-card">
            <h3>
              <span className="swatch" style={{ background: estimatorColor(estimators, id) }} />
              {label}
            </h3>
            <div>In-tunnel RMSE: <b>{fmt(m.rmse_in_tunnel_m, 'm')}</b></div>
            {exits.length === 0 && <div>Tunnel exit error: <b>n/a</b></div>}
            {exits.map(([tid, v]) => (
              <div key={tid}>Exit error ({tid}): <b>{fmt(v, 'm')}</b></div>
            ))}
          </section>
        )
      })}
    </aside>
  )
}
