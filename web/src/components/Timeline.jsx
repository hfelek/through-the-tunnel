// Minimal time slider; T7.4 replaces it with full playback controls.
export default function Timeline({ duration, t, onChange }) {
  return (
    <section className="timeline">
      <input
        type="range"
        min={0}
        max={duration ?? 0}
        step={0.1}
        value={t}
        disabled={duration == null}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      <span className="time-readout">t = {t.toFixed(1)} s</span>
    </section>
  )
}
