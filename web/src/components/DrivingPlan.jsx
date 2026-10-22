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

/** One plan point on one line with labelled fields (nothing wraps or is cut off; the panel is wide enough). */
function PointRow({ p, onPatch, onDelete }) {
  const meters = (key) => (v) => v !== undefined && onPatch({ [key]: Math.round(v * 1000) })
  const required = (key) => (v) => v !== undefined && onPatch({ [key]: v })
  const optional = (key) => (v) => onPatch({ [key]: v }) // empty = back to the default 1.5 m/s²
  const km_ = (key, value) => <Num value={km(value)} step={0.1} width={78} onValue={meters(key)} />
  const range = (key) => (
    <>
      <Num value={p[key][0]} width={60} onValue={(v) => v !== undefined && onPatch({ [key]: [v, Math.max(v, p[key][1])] })} />–
      <Num value={p[key][1]} width={60} onValue={(v) => v !== undefined && onPatch({ [key]: [Math.min(p[key][0], v), v] })} />
    </>
  )
  let body
  if (p.type === 'speed') {
    body = <>at {km_('s', p.s)} km → <Num value={p.kmh} min={1} width={64} onValue={required('kmh')} /> km/h, rate <Num value={p.rate_mps2} step={0.1} width={64} placeholder="1.5" onValue={optional('rate_mps2')} /> m/s²</>
  } else if (p.type === 'stop') {
    body = <>at {km_('s', p.s)} km, wait <Num value={p.dwell_s} width={64} onValue={required('dwell_s')} /> s, brake <Num value={p.decel_mps2} step={0.1} width={64} placeholder="1.5" onValue={optional('decel_mps2')} /> accel <Num value={p.accel_mps2} step={0.1} width={64} placeholder="1.5" onValue={optional('accel_mps2')} /> m/s²</>
  } else {
    body = <>from {km_('from_s', p.from_s)} to {km_('to_s', p.to_s)} km, <Num value={p.kmh} min={1} width={64} onValue={required('kmh')} /> km/h, stops {range('stop_s')} s, go {range('go_s')} s</>
  }
  return (
    <div className="plan-row">
      <span className="plan-type">{p.type === 'speed' ? 'Speed' : p.type === 'stop' ? 'Stop' : 'Traffic'}</span>
      {body}
      <button className="secondary plan-del" title="Delete this point" onClick={onDelete}>×</button>
    </div>
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
      {car.plan.map((p, i) => (
        <PointRow key={`${i}-${p.type}`} p={p} onPatch={(patch) => apply(E.editPlanPoint(scenario, i, patch))} onDelete={() => apply(E.deletePlanPoint(scenario, i))} />
      ))}
      <div className="ctl-row">
        <button className="secondary" onClick={() => apply(E.addPlanPoint(scenario, 'speed'))}>+ Speed point</button>
        <button className="secondary" onClick={() => apply(E.addPlanPoint(scenario, 'stop'))}>+ Stop</button>
        <button className="secondary" onClick={() => apply(E.addPlanPoint(scenario, 'traffic'))}>+ Traffic section</button>
      </div>
    </section>
  )
}
