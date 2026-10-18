import { useCallback, useEffect, useState } from 'react'
import { timeToX, xToTime } from '../lib/plotGeometry'

/** Shared frame for the time-aligned charts: measures the width, draws the cursor and handles click-to-seek. */
export default function ChartStack({ duration, t, onSeek, children }) {
  const [el, setEl] = useState(null)
  const [w, setW] = useState(800)
  useEffect(() => {
    if (!el) return
    const ro = new ResizeObserver(([e]) => setW(Math.max(200, Math.round(e.contentRect.width))))
    ro.observe(el)
    return () => ro.disconnect()
  }, [el])

  const onClick = useCallback((e) => {
    if (!duration || !e.target.closest('.chart-row')) return // controls rows never seek
    const r = e.currentTarget.getBoundingClientRect()
    onSeek(xToTime(e.clientX - r.left, duration, r.width))
  }, [duration, onSeek])

  if (!duration) return <section className="charts empty">Run a scenario to see the charts.</section>
  return (
    <section className="charts">
      <div className="chart-stack" ref={setEl} onClick={onClick}>
        {children(w)}
        <div className="chart-cursor" style={{ left: timeToX(t, duration, w) }} />
      </div>
    </section>
  )
}
