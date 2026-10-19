import { interpAt } from './interp'

/** Run duration: last truth t, or the last estimate t if there is no truth. */
export function vehicleDuration(vehicle) {
  const t = vehicle?.truth?.t?.length
    ? vehicle.truth.t
    : Object.values(vehicle?.estimates ?? {})[0]?.t
  return t?.length ? t[t.length - 1] : null
}

/** Tunnel intervals from tunnel_enter / tunnel_exit events (an unclosed tunnel runs to the end). */
export function tunnelIntervals(events, duration) {
  const open = {}
  const out = []
  for (const ev of events ?? []) {
    if (ev.type === 'tunnel_enter') open[ev.ref] = ev.t
    else if (ev.type === 'tunnel_exit' && open[ev.ref] != null) {
      out.push({ ref: ev.ref, start: open[ev.ref], end: ev.t })
      delete open[ev.ref]
    }
  }
  for (const [ref, start] of Object.entries(open)) out.push({ ref, start, end: duration })
  return out.sort((a, b) => a.start - b.start)
}

export const RAW_MARKER_GAP_M = 5 // show the raw s as a second marker only when the display is this far from it

/** Estimate at time t: `s` (raw, the bar's centre), `shown` = display_s when present (T8.6), else s. */
export function estimateAt(e, t) {
  const s = interpAt(e.t, e.s, t)
  const shown = e.display_s?.length ? interpAt(e.t, e.display_s, t) : s
  return { s, shown, held: Math.abs(shown - s) > RAW_MARKER_GAP_M }
}
