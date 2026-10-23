const UNREACHABLE = 'API not reachable. Is make dev running?'

function formatDetail(detail) {
  if (Array.isArray(detail)) {
    return detail
      .map((d) => `${(d.loc || []).filter((p) => p !== 'body').join('.')}: ${d.msg}`)
      .join('\n')
  }
  return typeof detail === 'string' ? detail : JSON.stringify(detail)
}

async function request(path, options) {
  let res
  try {
    res = await fetch(path, options)
  } catch {
    throw new Error(UNREACHABLE)
  }
  if (!res.ok) {
    let message = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (body.detail !== undefined) message = formatDetail(body.detail)
    } catch {
      // body was not JSON; keep the status text
    }
    throw new Error(message)
  }
  return res.json()
}

export const getScenarios = () => request('/api/scenarios')
export const getScenario = (id) => request(`/api/scenarios/${encodeURIComponent(id)}`)
export const getEstimators = () => request('/api/estimators')
export const getPresets = () => request('/api/presets')

export const simulate = (scenario, estimators, decimateHz = 10, calloutK = 1.0) =>
  request('/api/simulate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      scenario,
      estimators,
      decimate_hz: decimateHz,
      callout_k: calloutK,
    }),
  })


export const getRecordings = () => request('/api/real')

export const runReal = (id, outageStart, outageEnd, estimators, decimateHz = 10) =>
  request(`/api/real/${encodeURIComponent(id)}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ outage_start_s: outageStart, outage_end_s: outageEnd, estimators, decimate_hz: decimateHz }),
  })

export const monteCarlo = (scenario, estimators, nSeeds) =>
  request('/api/montecarlo', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario, estimators, n_seeds: nSeeds }),
  })
