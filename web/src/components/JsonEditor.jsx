import { useState } from 'react'

/** Position-aware message for a JSON.parse failure. */
function describe(err, text) {
  const m = /position (\d+)/.exec(err.message)
  if (!m || /line \d+/.test(err.message)) return err.message
  const before = text.slice(0, Number(m[1])).split('\n')
  return `${err.message} (line ${before.length}, column ${before[before.length - 1].length + 1})`
}

/** Drawer with the scenario JSON as text. Mounted only while open, so it re-seeds from state every time. */
export default function JsonEditor({ scenario, onApply, onClose }) {
  const [text, setText] = useState(() => JSON.stringify(scenario, null, 2))
  const [error, setError] = useState(null)
  const apply = () => {
    let parsed
    try {
      parsed = JSON.parse(text)
    } catch (e) {
      setError(describe(e, text))
      return
    }
    if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
      setError('The scenario must be a JSON object.')
      return
    }
    onApply(parsed)
  }
  return (
    <div className="json-drawer" role="dialog" aria-label="Scenario JSON">
      <div className="json-head">
        <b>Scenario JSON</b>
        <span className="muted">Schema errors are reported by the API on Run.</span>
      </div>
      <textarea className="json-text" value={text} spellCheck={false} onChange={(e) => { setText(e.target.value); setError(null) }} />
      {error && <div className="error-box">{error}</div>}
      <div className="json-actions">
        <button onClick={apply}>Apply</button>
        <button className="secondary" onClick={onClose}>Cancel</button>
      </div>
    </div>
  )
}
