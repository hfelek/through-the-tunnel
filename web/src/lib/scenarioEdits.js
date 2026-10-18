// Pure scenario edits: each takes a scenario and returns a new one. The controls and the JSON editor share one object.

export const MIN_TAIL_M = 1000 // road that must remain after the last tunnel
export const MIN_TUNNEL_GAP_M = 100 // between the first tunnel's end and the next tunnel's start
export const MAX_TUNNEL_M = 5000
export const MIN_TUNNEL_M = 500

const clone = (sc) => structuredClone(sc)
const car = (sc) => sc.vehicles[0]
export const roadLength = (sc) => sc.road.segments.reduce((a, s) => a + s.length_m, 0)

export const tunnelLength = (sc) => (sc.road.tunnels[0] ? sc.road.tunnels[0].end_s - sc.road.tunnels[0].start_s : 0)

/** Longest length the first tunnel can take (the slider maximum): stays clear of the next tunnel. */
export function maxTunnelLength(sc) {
  const [first, next] = sc.road.tunnels
  if (!first) return 0
  return next ? Math.min(MAX_TUNNEL_M, next.start_s - MIN_TUNNEL_GAP_M - first.start_s) : MAX_TUNNEL_M
}

/** Grows the road to `newLen`: a straight tail is lengthened, an arc tail gets a new straight (keeps the shape). */
function extendRoad(sc, oldLen, newLen) {
  const last = sc.road.segments[sc.road.segments.length - 1]
  const extra = newLen - oldLen
  if (last.type === 'straight') last.length_m += extra
  else sc.road.segments.push({ type: 'straight', length_m: extra, grade_pct: last.grade_pct ?? 0 })
  const limits = sc.road.speed_limits
  if (limits.length) limits[limits.length - 1].to_s = newLen
  for (const v of sc.vehicles) {
    for (const p of v.profile) if (p.type === 'cruise' && p.until_s === oldLen) p.until_s = newLen
  }
}

export function setTunnelLength(sc, lengthM) {
  const out = clone(sc)
  const first = out.road.tunnels[0]
  if (!first) return out
  const len = Math.min(Math.max(lengthM, Math.min(MIN_TUNNEL_M, maxTunnelLength(sc))), maxTunnelLength(sc))
  first.end_s = first.start_s + len
  const oldLen = roadLength(out)
  const lastEnd = Math.max(...out.road.tunnels.map((t) => t.end_s))
  const newLen = Math.max(oldLen, lastEnd + MIN_TAIL_M)
  if (newLen > oldLen) extendRoad(out, oldLen, newLen)
  for (const e of out.road.exits) e.s = Math.min(e.s, newLen)
  return out
}

export const exitPos = (sc) => sc.road.exits[0]?.s ?? 0

export function setExitPos(sc, s) {
  const out = clone(sc)
  if (out.road.exits[0]) out.road.exits[0].s = Math.min(Math.max(s, 0), roadLength(out))
  return out
}

/** null when the 60 s stop can be added, otherwise the reason it cannot. */
export function stopBlockedReason(sc) {
  const p = car(sc).profile
  if (p.length !== 1 || p[0].type !== 'cruise') return "car1's profile is not a single cruise"
  const tun = sc.road.tunnels[0]
  if (!tun) return 'the road has no tunnel'
  if ((tun.start_s + tun.end_s) / 2 - 300 <= car(sc).start_s) return 'the tunnel midpoint is too close to the start'
  return null
}

export function addStopInTunnel(sc) {
  if (stopBlockedReason(sc)) return sc
  const out = clone(sc)
  const { start_s, end_s } = out.road.tunnels[0]
  const mid = (start_s + end_s) / 2
  const kmh = car(out).profile[0].kmh
  car(out).profile = [
    { type: 'cruise', kmh, until_s: mid - 300 },
    { type: 'stop', at_s: mid, decel_mps2: 1.5, dwell_s: 60 },
    { type: 'ramp', to_kmh: kmh, accel_mps2: 1.2 },
    { type: 'cruise', kmh, until_s: roadLength(out) },
  ]
  return out
}

export const cruiseSpeed = (sc) => car(sc).initial_kmh

export function setCruiseSpeed(sc, kmh) {
  const out = clone(sc)
  car(out).initial_kmh = kmh
  for (const p of car(out).profile) {
    if (p.type === 'cruise') p.kmh = kmh
    else if (p.type === 'ramp') p.to_kmh = kmh
  }
  return out
}

function edit(sc, fn) {
  const out = clone(sc)
  fn(out)
  return out
}

export const setPhonePreset = (sc, preset) => edit(sc, (o) => { car(o).phone.preset = preset })
export const setMountPitch = (sc, deg) => edit(sc, (o) => { car(o).phone.mount.pitch_deg = deg })
export const setFanNoise = (sc, pa) => edit(sc, (o) => { o.tunnel_env.fan_pressure_noise_pa = pa })
export const setBeacons = (sc, patch) => edit(sc, (o) => { Object.assign(o.beacons, patch) })
export const setSeed = (sc, seed) => edit(sc, (o) => { o.seed = seed })
