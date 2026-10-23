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
function ParamName({ name, info, onToggle }) {
  return (
    <span className="param-name">
      {info?.label ?? name}
      {info?.description && (
        <button type="button" className="info-i" title={info.description} aria-label={`About ${info.label}`} onClick={onToggle}>i</button>
      )}
    </span>
  )
}

/** The long description opens in its own row below the input (a full-width cell of the parameter grid). */
function ParamDesc({ name, info }) {
  return <span className="param-desc">{info.description} <span className="muted">({name})</span></span>
}

function ParamInput({ name, info, value, constraint, onCommit }) {
  const [draft, setDraft] = useState(null)
  const [err, setErr] = useState(null)
  const [open, setOpen] = useState(false)
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
      <ParamName name={name} info={info} onToggle={() => setOpen((o) => !o)} />
      <input
        type="number" step={isInt ? 1 : 'any'} min={constraint?.min ?? constraint?.gt}
        value={draft ?? value}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => e.key === 'Enter' && commit()}
      />
      <span className="param-unit">{info?.unit}</span>{/* always rendered: an empty cell keeps the columns aligned */}
      {open && info?.description && <ParamDesc name={name} info={info} />}
      {err && <span className="param-err">{err}</span>}
    </label>
  )
}

/** On/off parameter (constraint type "bool"): a checkbox that commits at once. */
function BoolInput({ name, info, value, onCommit }) {
  const [open, setOpen] = useState(false)
  return (
    <label className="param">
      <ParamName name={name} info={info} onToggle={() => setOpen((o) => !o)} />
      <input type="checkbox" checked={Boolean(value)} onChange={(e) => onCommit(e.target.checked)} />
      <span className="param-unit" />
      {open && info?.description && <ParamDesc name={name} info={info} />}
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
              <div className="params">
              {Object.keys(e.params).map((name) => {
                const value = params[e.id]?.[name] ?? e.params[name]
                const onCommit = (v) => onParam(e.id, name, v)
                return e.constraints?.[name]?.type === 'bool'
                  ? <BoolInput key={name} name={name} info={e.param_info?.[name]} value={value} onCommit={onCommit} />
                  : <ParamInput key={name} name={name} info={e.param_info?.[name]} value={value} constraint={e.constraints?.[name]} onCommit={onCommit} />
              })}
              </div>
              <button className="link" onClick={() => onReset(e.id)}>Reset</button>
            </details>
          )}
        </div>
      ))}
    </div>
  )
})
