import { useEffect, useRef, useState } from 'react'
import { interpAt } from '../lib/interp'
import { roadPointAt } from '../lib/road'
import { estimatorColor, TRUTH_COLOR } from '../colors'
import { ExitLayer, RoadLayer } from './MapStatic'
import MapDynamic from './MapDynamic'

const HEIGHT = 360
const FOLLOW_VIEW_M = 1000 // visible width when following the car
const MIN_SCALE = 0.01 // px per metre
const MAX_SCALE = 20

export default function MapView({ trace, estimators, t }) {
  // callback refs (state): the svg only exists once a trace is present
  const [wrapEl, setWrapEl] = useState(null)
  const [svgEl, setSvgEl] = useState(null)
  const [w, setW] = useState(800)
  // scale null = default (FOLLOW_VIEW_M across the width)
  const [view, setView] = useState({ cx: 0, cy: 0, scale: null, follow: true })

  useEffect(() => {
    if (!wrapEl) return
    const ro = new ResizeObserver(([e]) => setW(Math.max(200, e.contentRect.width)))
    ro.observe(wrapEl)
    return () => ro.disconnect()
  }, [wrapEl])

  const vehicle = trace?.vehicles?.[0]
  const map = trace?.map
  const sTrue = vehicle?.truth?.t?.length ? interpAt(vehicle.truth.t, vehicle.truth.s, t) : null
  const car = map && sTrue != null ? roadPointAt(map, sTrue) : null
  const scale = view.scale ?? w / FOLLOW_VIEW_M
  const follow = view.follow && car != null
  const cx = follow ? car.x : view.cx
  const cy = follow ? car.y : view.cy

  // the wheel listener must be non-passive to stop page scrolling
  const latest = useRef()
  useEffect(() => {
    latest.current = { w, cx, cy, scale, follow }
  })
  useEffect(() => {
    const svg = svgEl
    if (!svg) return
    const onWheel = (ev) => {
      ev.preventDefault()
      const L = latest.current
      const rect = svg.getBoundingClientRect()
      const px = ev.clientX - rect.left
      const py = ev.clientY - rect.top
      const next = Math.min(MAX_SCALE, Math.max(MIN_SCALE, L.scale * Math.exp(-ev.deltaY * 0.0015)))
      setView((v) => {
        if (L.follow) return { ...v, scale: next } // car stays centered
        const wx = L.cx + (px - L.w / 2) / L.scale
        const wy = L.cy - (py - HEIGHT / 2) / L.scale
        return { ...v, scale: next, cx: wx - (px - L.w / 2) / next, cy: wy + (py - HEIGHT / 2) / next }
      })
    }
    svg.addEventListener('wheel', onWheel, { passive: false })
    return () => svg.removeEventListener('wheel', onWheel)
  }, [svgEl])

  const drag = useRef(null)
  const onPointerDown = (ev) => {
    drag.current = { x: ev.clientX, y: ev.clientY }
    ev.currentTarget.setPointerCapture(ev.pointerId)
  }
  const onPointerMove = (ev) => {
    if (!drag.current) return
    const dx = ev.clientX - drag.current.x
    const dy = ev.clientY - drag.current.y
    drag.current = { x: ev.clientX, y: ev.clientY }
    if (dx === 0 && dy === 0) return
    const L = latest.current
    setView((v) => ({ ...v, follow: false, scale: L.scale, cx: L.cx - dx / L.scale, cy: L.cy + dy / L.scale }))
  }
  const onPointerUp = () => { drag.current = null }

  const toggleFollow = () =>
    setView((v) => (v.follow ? { ...v, follow: false, cx, cy, scale } : { ...v, follow: true, scale: null }))

  const geom = { cx, cy, scale, w, h: HEIGHT }
  if (!map || !vehicle) {
    return (
      <section className="map-view empty" ref={setWrapEl} style={{ height: HEIGHT }}>
        Run a scenario to see the map.
      </section>
    )
  }

  return (
    <section className="map-view" ref={setWrapEl} style={{ height: HEIGHT }}>
      <svg
        ref={setSvgEl}
        width={w}
        height={HEIGHT}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        <RoadLayer map={map} {...geom} />
        <ExitLayer map={map} {...geom} />
        <MapDynamic map={map} vehicle={vehicle} estimators={estimators} t={t} {...geom} />
      </svg>
      <label className="follow-toggle">
        <input type="checkbox" checked={follow} onChange={toggleFollow} disabled={car == null} /> Follow car
      </label>
      <div className="legend">
        <span><i className="dot" style={{ background: TRUTH_COLOR }} /> Truth</span>
        {Object.keys(vehicle.estimates ?? {}).map((id) => (
          <span key={id}>
            <i className="dot hollow" style={{ borderColor: estimatorColor(estimators, id) }} />
            {estimators.find((e) => e.id === id)?.label ?? id}
          </span>
        ))}
        <span><i className="dot gnss" /> GNSS fix (last 10 s)</span>
      </div>
    </section>
  )
}
