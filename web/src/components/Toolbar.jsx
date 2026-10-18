export default function Toolbar({ state, onSelect, onRun }) {
  const { scenarios, scenarioId, scenario, loading, error } = state
  const current = scenarios.find((s) => s.id === scenarioId)
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
            {s.id}
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
      {current && <span className="description">{current.description}</span>}
      {error && <div className="error-box">{error}</div>}
    </header>
  )
}
