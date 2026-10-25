import { realParamsFor, withRealDefaults } from './lib/realDefaults'

export const initialState = {
  scenarios: [],
  scenarioId: null,
  scenario: null, // single source of truth for the scenario JSON
  estimators: [], // registry entries: {id, label, params, constraints}
  selected: [], // ids of the estimators that Run sends
  params: {}, // current parameter values per estimator id
  realParams: {}, // the same for real mode: starts at the recording's default_params (T10.6c)
  trace: null, // replaced as a whole, never mutated
  outdated: false, // the scenario was edited after the shown trace was computed
  presets: {},
  calloutK: 1.0, // run parameter, not part of the scenario
  autoRun: false,
  source: 'sim', // 'sim' = scenarios, 'real' = replay of a recording with a GNSS outage (T10.5b)
  recordings: [], // from GET /api/real: {id, title, span_s, default_outage_s}
  recordingId: null,
  outage: ['515', '625'], // recording seconds, kept as text while the user types
  runId: 0, // id of the latest run; responses of older runs are ignored
  loading: false,
  error: null,
}

const paramsKey = (state) => (state.source === 'real' ? 'realParams' : 'params')

/** Select a recording: its outage window and its default parameters replace the current ones. */
function withRecording(state, id) {
  const rec = state.recordings.find((r) => r.id === id)
  return {
    ...state,
    recordingId: rec?.id ?? null,
    outage: rec ? rec.default_outage_s.map(String) : initialState.outage,
    realParams: realParamsFor(state.estimators, rec),
  }
}

export function reducer(state, action) {
  switch (action.type) {
    case 'scenarios_loaded':
      return { ...state, scenarios: action.scenarios }
    case 'estimators_loaded':
      return {
        ...state,
        estimators: action.estimators,
        selected: action.estimators.map((e) => e.id),
        params: Object.fromEntries(action.estimators.map((e) => [e.id, { ...e.params }])),
        realParams: realParamsFor(action.estimators, state.recordings.find((r) => r.id === state.recordingId)),
      }
    case 'toggle_estimator': {
      const on = state.selected.includes(action.id)
      const selected = state.estimators.map((e) => e.id).filter((id) => (id === action.id ? !on : state.selected.includes(id)))
      return { ...state, selected, outdated: state.trace != null }
    }
    case 'set_param': {
      const key = paramsKey(state) // the store of the active mode
      return {
        ...state,
        [key]: { ...state[key], [action.id]: { ...state[key][action.id], [action.name]: action.value } },
        outdated: state.trace != null,
      }
    }
    case 'reset_params': {
      const key = paramsKey(state)
      const recording = state.recordings.find((r) => r.id === state.recordingId)
      const known = state.source === 'real' ? withRealDefaults(state.estimators, recording) : state.estimators
      const defaults = known.find((e) => e.id === action.id)?.params ?? {}
      return { ...state, [key]: { ...state[key], [action.id]: { ...defaults } }, outdated: state.trace != null }
    }
    case 'recordings_loaded':
      return withRecording({ ...state, recordings: action.recordings }, action.recordings[0]?.id)
    case 'select_recording':
      return withRecording({ ...state, trace: null, outdated: false, error: null }, action.id)
    case 'set_outage':
      return { ...state, outage: state.outage.map((v, i) => (i === action.index ? action.value : v)), outdated: state.trace != null }
    case 'set_source':
      return { ...state, source: action.source, trace: null, outdated: false, error: null }
    case 'presets_loaded':
      return { ...state, presets: action.presets }
    case 'select_scenario':
      return { ...state, scenarioId: action.id, scenario: null, trace: null, outdated: false, error: null }
    case 'edit_scenario':
      return { ...state, scenario: action.scenario, outdated: state.trace != null }
    case 'set_callout_k':
      return { ...state, calloutK: action.value, outdated: state.trace != null }
    case 'set_auto_run':
      return { ...state, autoRun: action.value }
    case 'scenario_loaded':
      return action.id === state.scenarioId ? { ...state, scenario: action.scenario } : state
    case 'run_start':
      return { ...state, loading: true, error: null, runId: action.runId }
    case 'run_done':
      return action.runId === state.runId ? { ...state, loading: false, trace: action.trace, outdated: false } : state
    case 'run_failed':
      return action.runId === state.runId ? { ...state, loading: false, error: action.message } : state
    case 'error':
      return { ...state, error: action.message }
    default:
      return state
  }
}
