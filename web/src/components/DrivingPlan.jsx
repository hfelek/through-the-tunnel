import { useState } from 'react'
import * as E from '../lib/scenarioEdits'

/** Number input that keeps its own text while typing and commits (runs) on Enter or blur. Empty = `onValue(undefined)`. */
function Num({ value, step = 1, min = 0, width = 56, placeholder, onValue }) {
  const [text, setText] = useState(null) // null = show the scenario's value
  const commit = () => {
    if (text === null) return
    const v = text.trim() === '' ? undefined : Number(text)
    setText(null)
    if (v === undefined ? value !== undefined : Number.isFinite(v) && v !== value) onValue(v)
  }
  return (
    <input
      type="number" className="plan-num" style={{ width }} step={step} min={min} placeholder={placeholder}
      value={text ?? (value ?? '')}
      onChange={(e) => setText(e.target.value)} onBlur={commit} onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.blur()}
    />
  )
}

const km = (m) => Math.round(m) / 1000

function PointRow({ p, onPatch, onDelete }) {
  const meters = (key) => (v) => v !== undefined && onPatch({ [key]: Math.round(v * 1000) })
  const required = (key) => (v) => v !== undefined && onPatch({ [key]: v })
  const pos = p.type === 'traffic'
    ? <><Num value={km(p.from_s)} step={0.1} onValue={meters('from_s')} />–<Num value={km(p.to_s)} step={0.1} onValue={meters('to_s')} /></>
    : <Num value={km(p.s)} step={0.1} onValue={meters('s')} />
  let value, rate
  if (p.type === 'speed') {
    value = <><Num value={p.kmh} min={1} onValue={required('kmh')} /> km/h</>
    rate = <Num value={p.rate_mps2} step={0.1} placeholder="1.5" onValue={(v) => onPatch({ rate_mps2: v })} />
  } else if (p.type === 'stop') {
    value = <><Num value={p.dwell_s} onValue={required('dwell_s')} /> s</>
    rate = <>
      <Num value={p.decel_mps2} step={0.1} width={44} placeholder="1.5" onValue={(v) => onPatch({ decel_mps2: v })} />
      <Num value={p.accel_mps2} step={0.1} width={44} placeholder="1.5" onValue={(v) => onPatch({ accel_mps2: v })} />
    </>
  } else {
    const range = (key, label) => (
      <span>{label} <Num value={p[key][0]} width={40} onValue={(v) => v !== undefined && onPatch({ [key]: [v, Math.max(v, p[key][1])] })} />–
        <Num value={p[key][1]} width={40} onValue={(v) => v !== undefined && onPatch({ [key]: [Math.min(p[key][0], v), v] })} /> s</span>
    )
    value = <><Num value={p.kmh} min={1} onValue={required('kmh')} /> km/h {range('stop_s', 'stops')} {range('go_s', 'go')}</>
    rate = null
  }
  return (
    <tr>
      <td>{p.type}</td>
      <td className="nowrap">{pos}</td>
      <td>{value}</td>
      <td className="nowrap">{rate}</td>
      <td><button className="secondary plan-del" title="Delete this point" onClick={onDelete}>×</button></td>
    </tr>
  )
}

/** Editable driving plan of car1 (docs/CONTRACTS.md 3.2). Every edit goes through onEdit(newScenario, true) and runs. */
export default function DrivingPlan({ scenario, onEdit }) {
  const car = scenario.vehicles[0]
  const apply = (next) => onEdit(next, true)
  return (
    <section className="plan">
      <h3>Driving plan</h3>
      <div className="ctl-row">
        <label>Start speed <Num value={car.initial_kmh} min={0} onValue={(v) => v !== undefined && apply(E.setInitialSpeed(scenario, v))} /> km/h</label>
      </div>
      {car.plan.length > 0 && (
        <table className="plan-table">
          <thead><tr><th>Type</th><th>km</th><th>Value</th><th title="Speed: rate. Stop: braking, then accelerating (m/s², default 1.5)">m/s²</th><th /></tr></thead>
          <tbody>
            {car.plan.map((p, i) => (
              <PointRow key={`${i}-${p.type}`} p={p} onPatch={(patch) => apply(E.editPlanPoint(scenario, i, patch))} onDelete={() => apply(E.deletePlanPoint(scenario, i))} />
            ))}
          </tbody>
        </table>
      )}
      <div className="ctl-row">
        <button className="secondary" onClick={() => apply(E.addPlanPoint(scenario, 'speed'))}>+ Speed point</button>
        <button className="secondary" onClick={() => apply(E.addPlanPoint(scenario, 'stop'))}>+ Stop</button>
        <button className="secondary" onClick={() => apply(E.addPlanPoint(scenario, 'traffic'))}>+ Traffic section</button>
      </div>
    </section>
  )
}
