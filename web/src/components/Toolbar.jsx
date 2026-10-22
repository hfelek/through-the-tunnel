import { memo, useState } from 'react'
import InfoModal from './InfoModal'

export default memo(function Toolbar({ state, onSelect, onRun }) {
  const { scenarios, scenarioId, scenario, loading, error } = state
  const current = scenarios.find((s) => s.id === scenarioId)
  const [info, setInfo] = useState(false)
  return (
    <header className="toolbar">
      <h1>Through the Tunnel</h1>
      <select
        value={scenarioId ?? ''}
        disabled={loading}
        onChange={(e) => onSelect(e.target.value)}
      >
        {scenarios.map((s) => (
          <option key={s.id} value={s.id}>
            {s.title}
          </option>
        ))}
      </select>
      <button onClick={onRun} disabled={loading || !scenario}>
        Run
      </button>
      {loading && (
        <span className="loading">
          <span className="spinner" /> Simulating…
        </span>
      )}
      <button className="secondary info-btn" disabled={!current} onClick={() => setInfo(true)} title="About this scenario" aria-label="About this scenario">i</button>
      {info && current && <InfoModal title={current.title} text={current.description} onClose={() => setInfo(false)} />}
      {error && <div className="error-box">{error}</div>}
    </header>
  )
})
