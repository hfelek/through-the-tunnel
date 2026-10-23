import { memo, useState } from 'react'
import InfoModal from './InfoModal'
import { settingsSummary } from '../lib/summary'

const REAL_NOTE = 'A real drive recorded with a phone. GNSS is removed in the outage window, as if the car were in a tunnel, and the removed fixes serve as the truth (the GNSS projected on the map, accurate to about 5 m). The map comes from the drive\'s own GNSS. Times are recording seconds. The Methods picker starts at the recording\'s own defaults: the calibration limits are relaxed for a hilly city drive (max grade 0.03, max curvature 0.002). A replay takes about 10 s.'

export default memo(function Toolbar({ state, onSelect, onRun, onSource, onRecording, onOutage, settingsOpen, onToggleSettings }) {
  const { scenarios, scenarioId, scenario, loading, error, source, recordings, recordingId, outage } = state
  const real = source === 'real'
  const current = real
    ? { title: 'Real recording', description: REAL_NOTE }
    : scenarios.find((s) => s.id === scenarioId)
  const [info, setInfo] = useState(false)
  return (
    <header className="toolbar">
      <h1>Through the Tunnel</h1>
      <select value={source} disabled={loading} onChange={(e) => onSource(e.target.value)} aria-label="Source">
        <option value="sim">Simulation</option>
        <option value="real" disabled={recordings.length === 0}>Real recording</option>
      </select>
      {real ? (
        <>
          <select value={recordingId ?? ''} disabled={loading} onChange={(e) => onRecording(e.target.value)} aria-label="Recording">
            {recordings.map((r) => <option key={r.id} value={r.id}>{r.title}</option>)}
          </select>
          {[['Outage start', 0], ['end', 1]].map(([label, i]) => (
            <label key={i} className="outage">
              {label}
              <input type="number" step="1" value={outage[i]} disabled={loading} onChange={(e) => onOutage(i, e.target.value)} />
            </label>
          ))}
          <span className="muted">recording s</span>
        </>
      ) : (
        <select value={scenarioId ?? ''} disabled={loading} onChange={(e) => onSelect(e.target.value)}>
          {scenarios.map((s) => (
            <option key={s.id} value={s.id}>
              {s.title}
            </option>
          ))}
        </select>
      )}
      <button onClick={onRun} disabled={loading || (real ? !recordingId : !scenario)}>
        Run
      </button>
      <button className={`settings-btn${settingsOpen ? ' open' : ''}`} onClick={onToggleSettings} aria-expanded={settingsOpen}>
        Settings {settingsOpen ? '▴' : '▾'}
      </button>
      {!settingsOpen && (
        <span className="summary">{real ? `${state.selected.length} methods` : settingsSummary(scenario, state.selected.length)}</span>
      )}
      {loading && (
        <span className="loading">
          <span className="spinner" /> Simulating…
        </span>
      )}
      <button className="secondary info-btn" disabled={!current} onClick={() => setInfo(true)} title={real ? 'About the real recording' : 'About this scenario'} aria-label="About">i</button>
      {info && current && <InfoModal title={current.title} text={current.description} onClose={() => setInfo(false)} />}
      {error && <div className="error-box">{error}</div>}
    </header>
  )
})
