import { useMemo } from 'react'
import { interpAt } from '../lib/interp'
import { tunnelIntervals } from '../lib/trace'
import { SPEEDS } from '../lib/usePlayback'

const JUMP_LEAD_S = 5 // jump this long before the event so the change is visible

export default function Timeline({ trace, duration, t, playing, speed, onSeek, onToggle, onSpeed }) {
  const vehicle = trace?.vehicles?.[0]
  const disabled = duration == null
  const intervals = useMemo(() => tunnelIntervals(vehicle?.events, duration), [vehicle, duration])

  const truth = vehicle?.truth
  const hasTruth = truth?.t?.length > 0
  const kmh = hasTruth ? interpAt(truth.t, truth.v, t) * 3.6 : null
  const s = hasTruth ? interpAt(truth.t, truth.s, t) : null
  const inTunnel = s != null && trace.map.tunnels.some((tn) => s >= tn.start_s && s <= tn.end_s)
  const pct = (x) => `${(100 * x) / (duration || 1)}%`

  return (
    <section className="timeline">
      <div className="timeline-row">
        <button className="play" onClick={onToggle} disabled={disabled}>
          {playing ? 'Pause' : 'Play'}
        </button>
        <select value={speed} onChange={(e) => onSpeed(Number(e.target.value))} disabled={disabled} aria-label="Speed">
          {SPEEDS.map((v) => (
            <option key={v} value={v}>{v}x</option>
          ))}
        </select>
        <div className="slider-wrap">
          <div className="slider-bar">
            {intervals.map((iv) => (
              <div key={iv.ref} className="slider-tunnel" style={{ left: pct(iv.start), width: pct(iv.end - iv.start) }} title={iv.ref} />
            ))}
          </div>
          <input
            type="range"
            min={0}
            max={duration ?? 0}
            step={0.1}
            value={t}
            disabled={disabled}
            onChange={(e) => onSeek(Number(e.target.value))}
          />
        </div>
        <span className="time-readout">
          t = {t.toFixed(1)} s
          <br />
          {kmh != null ? `${kmh.toFixed(0)} km/h · ${inTunnel ? 'in tunnel' : 'open road'}` : '–'}
        </span>
      </div>
      {intervals.length > 0 && (
        <div className="timeline-row jumps">
          <span className="muted">Jump to:</span>
          {intervals.flatMap((iv) => [
            <button key={`${iv.ref}-in`} onClick={() => onSeek(iv.start - JUMP_LEAD_S)}>{iv.ref} entry</button>,
            <button key={`${iv.ref}-out`} onClick={() => onSeek(iv.end - JUMP_LEAD_S)}>{iv.ref} exit</button>,
          ])}
        </div>
      )}
    </section>
  )
}
