/** Run duration: last truth t, or the last estimate t if there is no truth. */
export function vehicleDuration(vehicle) {
  const t = vehicle?.truth?.t?.length
    ? vehicle.truth.t
    : Object.values(vehicle?.estimates ?? {})[0]?.t
  return t?.length ? t[t.length - 1] : null
}
