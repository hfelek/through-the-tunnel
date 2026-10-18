import { memo } from 'react'

const LENGTHS_M = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000]
const MIN_PX = 80
const MAX_PX = 160
const TARGET_PX = 120

/** Round length whose bar is 80-160 px (nearest 120 px), else the nearest available. */
function pickLength(scale) {
  const err = (m) => Math.abs(m * scale - TARGET_PX)
  const inRange = LENGTHS_M.filter((m) => m * scale >= MIN_PX && m * scale <= MAX_PX)
  return (inRange.length ? inRange : LENGTHS_M).reduce((a, b) => (err(b) < err(a) ? b : a))
}

const label = (m) => (m >= 1000 ? `${m / 1000} km` : `${m} m`)

export default memo(function ScaleBar({ scale }) {
  const m = pickLength(scale)
  return (
    <div className="scale-bar" style={{ width: m * scale }}>
      <div className="scale-line" />
      <span>{label(m)}</span>
    </div>
  )
})
