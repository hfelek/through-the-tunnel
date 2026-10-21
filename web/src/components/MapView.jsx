import { useEffect, useRef, useState } from 'react'
import { interpAt } from '../lib/interp'
import { roadPointAt } from '../lib/road'
import { roadRotation, screenToWorldOffset } from '../lib/mapProjection'
import { estimatorColor, estimatorShape, TRUTH_COLOR } from '../colors'
import EstimatorMarker from './EstimatorMarker'
import { ExitLayer, RoadPaths } from './MapStatic'
import MapDynamic from './MapDynamic'
import ScaleBar from './ScaleBar'
import NorthArrow from './NorthArrow'

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
  const [northUp, setNorthUp] = useState(false) // false: the road runs left to right

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
  const rot = map && !northUp ? roadRotation(map) : 0 // view rotation only; no data changes
  const scale = view.scale ?? w / FOLLOW_VIEW_M
  const follow = view.follow && car != null
  const cx = follow ? car.x : view.cx
  const cy = follow ? car.y : view.cy

  // the wheel listener must be non-passive to stop page scrolling
  const latest = useRef()
  useEffect(() => {
    latest.current = { w, cx, cy, scale, follow, rot }
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
        // keep the world point under the cursor fixed: its offset from the centre shrinks or grows with the scale
        const [ox, oy] = screenToWorldOffset(px - L.w / 2, py - HEIGHT / 2, L.scale, L.rot)
        const [nx, ny] = screenToWorldOffset(px - L.w / 2, py - HEIGHT / 2, next, L.rot)
        return { ...v, scale: next, cx: L.cx + ox - nx, cy: L.cy + oy - ny }
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
    const [wx, wy] = screenToWorldOffset(dx, dy, L.scale, L.rot) // the map follows the pointer, so the centre moves the other way
    setView((v) => ({ ...v, follow: false, scale: L.scale, cx: L.cx - wx, cy: L.cy - wy }))
  }
  const onPointerUp = () => { drag.current = null }

  const toggleFollow = () =>
    setView((v) => (v.follow ? { ...v, follow: false, cx, cy, scale } : { ...v, follow: true, scale: null }))

  const geom = { cx, cy, scale, w, h: HEIGHT, rot }
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
        <g transform={`translate(${w / 2} ${HEIGHT / 2}) scale(${scale} ${-scale}) rotate(${(rot * 180) / Math.PI}) translate(${-cx} ${-cy})`} fill="none" strokeLinejoin="round">
          <RoadPaths map={map} />
        </g>
        <ExitLayer map={map} {...geom} />
        <MapDynamic map={map} vehicle={vehicle} estimators={estimators} t={t} {...geom} />
      </svg>
      <label className="follow-toggle">
        <input type="checkbox" checked={follow} onChange={toggleFollow} disabled={car == null} /> Follow car
      </label>
      <div className="north-box">
        <NorthArrow rot={rot} />
        <label><input type="checkbox" checked={northUp} onChange={(e) => setNorthUp(e.target.checked)} /> North up</label>
      </div>
      <ScaleBar scale={scale} />
      <div className="legend">
        <span><i className="dot" style={{ background: TRUTH_COLOR }} /> Truth</span>
        {Object.keys(vehicle.estimates ?? {}).map((id) => (
          <span key={id}>
            <svg width={20} height={20} className="legend-marker">
              <EstimatorMarker shape={estimatorShape(estimators, id)} x={10} y={10} r={6} color={estimatorColor(estimators, id)} strokeWidth={2} />
            </svg>
            {estimators.find((e) => e.id === id)?.label ?? id}
          </span>
        ))}
        <span><i className="dot gnss" /> GNSS fix (last 10 s)</span>
      </div>
    </section>
  )
}
