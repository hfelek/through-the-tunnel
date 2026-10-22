import { memo, useState } from 'react'
import { estimatorColor } from '../colors'

/** Why `value` is not allowed by the constraint (null when it is fine). */
function violation(c = {}, value) {
  if (!Number.isFinite(value)) return 'enter a number'
  if (c.type === 'int' && !Number.isInteger(value)) return 'must be an integer'
  if (c.min !== undefined && value < c.min) return `must be ≥ ${c.min}`
  if (c.gt !== undefined && value <= c.gt) return `must be > ${c.gt}`
  return null
}

/** Number input that keeps a text draft and commits on blur / Enter; a bad value is rejected with a hint. */
function ParamName({ name, info }) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <span className="param-name">
        {info?.label ?? name}
        {info?.description && (
          <button type="button" className="info-i" title={info.description} aria-label={`About ${info.label}`} onClick={() => setOpen((o) => !o)}>i</button>
        )}
      </span>
      {open && <span className="param-desc">{info.description} <span className="muted">({name})</span></span>}
    </>
  )
}

function ParamInput({ name, info, value, constraint, onCommit }) {
  const [draft, setDraft] = useState(null)
  const [err, setErr] = useState(null)
  const commit = () => {
    if (draft === null) return
    const v = draft.trim() === '' ? NaN : Number(draft)
    const problem = violation(constraint, v)
    setDraft(null)
    setErr(problem ? `${name} ${problem}` : null)
    if (!problem && v !== value) onCommit(v)
  }
  const isInt = constraint?.type === 'int'
  return (
    <label className="param">
      <ParamName name={name} info={info} />
      <input
        type="number" step={isInt ? 1 : 'any'} min={constraint?.min ?? constraint?.gt}
        value={draft ?? value}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => e.key === 'Enter' && commit()}
      />
      {info?.unit && <span className="param-unit">{info.unit}</span>}
      {err && <span className="param-err">{err}</span>}
    </label>
  )
}

/** On/off parameter (constraint type "bool"): a checkbox that commits at once. */
function BoolInput({ name, info, value, onCommit }) {
  return (
    <label className="param">
      <ParamName name={name} info={info} />
      <input type="checkbox" checked={Boolean(value)} onChange={(e) => onCommit(e.target.checked)} />
    </label>
  )
}

export default memo(function EstimatorPicker({ estimators, selected, params, onToggle, onParam, onReset }) {
  return (
    <div className="picker">
      {estimators.length === 0 && <p className="muted">No methods loaded.</p>}
      {estimators.map((e) => (
        <div key={e.id} className="picker-item">
          <label>
            <input type="checkbox" checked={selected.includes(e.id)} onChange={() => onToggle(e.id)} />
            <span className="swatch" style={{ background: estimatorColor(estimators, e.id) }} />
            {e.label}
          </label>
          {Object.keys(e.params).length > 0 && (
            <details>
              <summary>Params</summary>
              {Object.keys(e.params).map((name) => {
                const value = params[e.id]?.[name] ?? e.params[name]
                const onCommit = (v) => onParam(e.id, name, v)
                return e.constraints?.[name]?.type === 'bool'
                  ? <BoolInput key={name} name={name} info={e.param_info?.[name]} value={value} onCommit={onCommit} />
                  : <ParamInput key={name} name={name} info={e.param_info?.[name]} value={value} constraint={e.constraints?.[name]} onCommit={onCommit} />
              })}
              <button className="link" onClick={() => onReset(e.id)}>Reset</button>
            </details>
          )}
        </div>
      ))}
    </div>
  )
})
