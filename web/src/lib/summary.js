/** One-line description of the current settings, shown in the header while the Settings panel is closed. */
export function settingsSummary(scenario, selectedCount) {
  if (!scenario) return ''
  const tunnels = scenario.road.tunnels
  const km = (m) => Number((m / 1000).toFixed(2))
  const parts = []
  if (tunnels.length === 1) parts.push(`${km(tunnels[0].end_s - tunnels[0].start_s)} km tunnel`)
  else if (tunnels.length > 1) parts.push(`${tunnels.length} tunnels`)
  if (scenario.road.exits[0]) parts.push(`exit ${km(scenario.road.exits[0].s)} km`)
  const n = scenario.vehicles[0].plan.length
  parts.push(`${n} plan point${n === 1 ? '' : 's'}`)
  parts.push(`${selectedCount} method${selectedCount === 1 ? '' : 's'}`)
  return parts.join(' · ')
}
