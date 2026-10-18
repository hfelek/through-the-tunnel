// Shared plot geometry: every chart and the cursor overlay use these, so x maps identically.
export const Y_AXIS_W = 46
export const M = { top: 6, right: 14, bottom: 0, left: 0 }
export const X_AXIS_H = 18
export const TICK = { fontSize: 11, fill: '#6b7280' }
export const fmt = (v) => Number(v.toPrecision(5))

const plotLeft = Y_AXIS_W + M.left
const plotWidth = (w) => w - plotLeft - M.right

/** Pixel x (inside the chart stack) of time t. */
export const timeToX = (t, duration, w) => plotLeft + (t / duration) * plotWidth(w)

/** Inverse of timeToX, clamped to [0, duration]. */
export const xToTime = (x, duration, w) => Math.min(Math.max((x - plotLeft) / plotWidth(w), 0), 1) * duration
