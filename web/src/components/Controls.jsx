import { memo,useState } from 'react'
import * as E from '../lib/scenarioEdits'
import DrivingPlan from './DrivingPlan'

const COMMIT_KEYS = ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End', 'PageUp', 'PageDown']

/** Small "i" button: hover shows the text, click toggles it below the control. */
function InfoButton({ label, text, onToggle }) {
  return (
    <button type="button" className="info-i" title={text} aria-label={`About ${label}`}
      onClick={(e) => { e.preventDefault(); onToggle() }}>i</button>
  )
}

/** Range input that edits the JSON on every step but only commits (runs) on release. */
function Slider({ label, value, min, max, step, unit, hint, info, onChange, onCommit }) {
  const [open, setOpen] = useState(false)
  return (
    <label className="ctl">
      <span>
        {label}: <b>{Number(value.toFixed(2))}{unit}</b>{hint && <span className="muted"> {hint}</span>}
        {info && <> <InfoButton label={label} text={info} onToggle={() => setOpen((o) => !o)} /></>}
      </span>
      <input
        type="range" min={min} max={max} step={step} value={Math.min(Math.max(value, min), max)}
        onChange={(e) => onChange(Number(e.target.value))}
        onPointerUp={onCommit}
        onKeyUp={(e) => COMMIT_KEYS.includes(e.key) && onCommit()}
      />
      {open && <span className="ctl-info">{info}</span>}
    </label>
  )
}

const INFO = {
  preset: 'Which phone\'s sensor quality is simulated. Flagship: datasheet values of a phone IMU (Bosch BMI260), barometer and GNSS. Budget: the flagship values made 2-4x worse, since budget datasheets are rarely public. Sources: presets/README.md.',
  pitch: 'How the phone is tilted in its holder. 0° = lying flat, screen up, top pointing forward; 65° = top tilted up toward the driver. The estimators do not know this angle; they learn the phone\'s orientation from GNSS before the tunnel. Yaw and roll are set in Edit JSON.',
  calloutK: 'How early the exit callouts come when the position is uncertain. A callout fires when position + k x uncertainty reaches the callout point. 0 uses the estimate alone (late about half the time); higher values announce earlier. Default 1.',
}

/**
 * Settings panel (T7.9): quick controls in columns plus the Methods picker passed in as `methods`. Every one reads its value from the scenario and writes through onEdit(newScenario, commit);
 * commit=false only updates the JSON (slider drag), commit=true also runs when auto-run is on.
 */
export default memo(function Controls({ scenario, presets, calloutK, autoRun, onEdit, onCommit, onCalloutK, onAutoRun, onEditJson, onReset, methods }) {
  if (!scenario) return null
  const car = scenario.vehicles[0]
  const L = E.roadLength(scenario)
  const maxTun = E.maxTunnelLength(scenario)
  const presetIds = Object.keys(presets)
  if (!presetIds.includes(car.phone.preset)) presetIds.push(car.phone.preset)
  const live = (fn) => (v) => onEdit(fn(scenario, v), false)
  const now = (fn) => (v) => onEdit(fn(scenario, v), true)
  const [presetOpen, setPresetOpen] = useState(false)
  return (
    <section className="panel controls settings">
      <div className="ctl-row settings-top">
        <label><input type="checkbox" checked={autoRun} onChange={(e) => onAutoRun(e.target.checked)} /> Auto-run</label>
        <button className="secondary" onClick={onEditJson}>Edit JSON</button>
        <button className="secondary" onClick={onReset} title="Reload this scenario from its file, discarding edits">Reset to default</button>
      </div>
      <div className="settings-cols">
        <div className="settings-col">
          <h3>Road and tunnel</h3>
          {scenario.road.tunnels[0] && (
            <Slider label="Tunnel length" value={E.tunnelLength(scenario) / 1000} unit=" km" min={Math.min(0.5, maxTun / 1000)} max={maxTun / 1000} step={0.1}
              hint={maxTun < E.MAX_TUNNEL_M ? `(max ${maxTun / 1000} km, next tunnel)` : null}
              onChange={(v) => onEdit(E.setTunnelLength(scenario, Math.round(v * 1000)), false)} onCommit={onCommit} />
          )}
          {scenario.road.exits[0] && (
            <Slider label="Exit position" value={E.exitPos(scenario)} unit=" m" min={0} max={L} step={10} onChange={live(E.setExitPos)} onCommit={onCommit} />
          )}
        </div>
        <div className="settings-col">
          <h3>Phone and sensors</h3>
          <label className="ctl">
            <span>Phone preset{' '}  
              <InfoButton label="Phone preset" text={INFO.preset} onToggle={() => setPresetOpen((o) => !o)} />
            </span>
            <select value={car.phone.preset} onChange={(e) => now(E.setPhonePreset)(e.target.value)}>
              {presetIds.map((id) => <option key={id} value={id}>{presets[id]?.name || id}</option>)}
            </select>
            {presetOpen && <span className="ctl-info">{INFO.preset}</span>}
          </label>
          <Slider label="Mount pitch" value={car.phone.mount.pitch_deg} unit="°" min={0} max={90} step={1} info={INFO.pitch} onChange={live(E.setMountPitch)} onCommit={onCommit} />          
          <label className="ctl-row">
            <input type="checkbox" checked={scenario.beacons.enabled} onChange={(e) => onEdit(E.setBeacons(scenario, { enabled: e.target.checked }), true)} /> Beacons
          </label>
          <Slider label="Beacon spacing" value={scenario.beacons.spacing_m} unit=" m" min={100} max={1000} step={50}
            onChange={(v) => onEdit(E.setBeacons(scenario, { spacing_m: v }), false)} onCommit={onCommit} />
          <div className="ctl-row">
            <label>Seed <input type="number" className="seed" value={scenario.seed} step={1}
              onChange={(e) => Number.isInteger(Number(e.target.value)) && e.target.value !== '' && now(E.setSeed)(Number(e.target.value))} /></label>
            <button className="secondary" onClick={() => now(E.setSeed)(Math.floor(Math.random() * 100000))}>New seed</button>
          </div>
          <Slider label="Callout k" value={calloutK} unit="" min={0} max={3} step={0.1} info={INFO.calloutK} onChange={onCalloutK} onCommit={onCommit} />
        </div>
        <div className="settings-col">
          <h3>Methods</h3>
          {methods}
        </div>
      </div>
        <div className="settings-plan">
          <DrivingPlan scenario={scenario} onEdit={onEdit} />
          <Slider label="Speed fluctuation" value={car.speed_jitter_kmh} unit=" km/h" min={0} max={E.MAX_JITTER_KMH} step={0.5}
            hint="(typical deviation from the target speed)" onChange={live(E.setSpeedJitter)} onCommit={onCommit} />
        </div>
    </section>
  )
})
