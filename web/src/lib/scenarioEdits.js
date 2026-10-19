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

export const MAX_JITTER_KMH = 6 // above this the fluctuation breaks the A11 jerk limit (2 m/s^3), see CODE_TOUR

export const setInitialSpeed = (sc, kmh) => edit(sc, (o) => { car(o).initial_kmh = kmh })
export const setSpeedJitter = (sc, kmh) => edit(sc, (o) => { car(o).speed_jitter_kmh = kmh })

/** Where a plan point sits on the road (a traffic section counts from its start). */
export const pointPos = (p) => (p.type === 'traffic' ? p.from_s : p.s)
const pointEnd = (p) => (p.type === 'traffic' ? p.to_s : p.s)
const sortPlan = (plan) => plan.sort((a, b) => pointPos(a) - pointPos(b)) // the server needs the points sorted

/** Target speed (km/h) after the whole plan: new points start from it, so adding one never changes the speed by itself. */
function lastTarget(plan, initial) {
  const speeds = plan.filter((p) => p.type === 'speed')
  return speeds.length ? speeds[speeds.length - 1].kmh : initial
}

/** New point 500 m after the last one (or in the middle of the first tunnel for an empty plan). */
export function addPlanPoint(sc, type) {
  const out = clone(sc)
  const plan = car(out).plan
  const tun = out.road.tunnels[0]
  const from = plan.length ? Math.max(...plan.map(pointEnd)) + 500 : tun ? Math.round((tun.start_s + tun.end_s) / 2) : 1000
  const s = Math.min(from, roadLength(out))
  if (type === 'speed') plan.push({ type, s, kmh: lastTarget(plan, car(out).initial_kmh) })
  else if (type === 'stop') plan.push({ type, s, dwell_s: 10 })
  else plan.push({ type, from_s: s, to_s: Math.min(s + 500, roadLength(out)), kmh: 30, stop_s: [5, 15], go_s: [10, 30] })
  sortPlan(plan)
  return out
}

export function editPlanPoint(sc, index, patch) {
  const out = clone(sc)
  const plan = car(out).plan
  Object.assign(plan[index], patch)
  for (const k of Object.keys(patch)) if (patch[k] === undefined) delete plan[index][k] // an emptied optional rate falls back to its default
  sortPlan(plan)
  return out
}

export function deletePlanPoint(sc, index) {
  const out = clone(sc)
  car(out).plan.splice(index, 1)
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
