export const initialState = {
  scenarios: [],
  scenarioId: null,
  scenario: null, // single source of truth for the scenario JSON
  estimators: [], // registry entries: {id, label, params, constraints}
  selected: [], // ids of the estimators that Run sends
  params: {}, // current parameter values per estimator id
  trace: null, // replaced as a whole, never mutated
  outdated: false, // the scenario was edited after the shown trace was computed
  presets: {},
  calloutK: 1.0, // run parameter, not part of the scenario
  autoRun: true,
  runId: 0, // id of the latest run; responses of older runs are ignored
  loading: false,
  error: null,
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
      }
    case 'toggle_estimator': {
      const on = state.selected.includes(action.id)
      const selected = state.estimators.map((e) => e.id).filter((id) => (id === action.id ? !on : state.selected.includes(id)))
      return { ...state, selected, outdated: state.trace != null }
    }
    case 'set_param':
      return {
        ...state,
        params: { ...state.params, [action.id]: { ...state.params[action.id], [action.name]: action.value } },
        outdated: state.trace != null,
      }
    case 'reset_params': {
      const defaults = state.estimators.find((e) => e.id === action.id)?.params ?? {}
      return { ...state, params: { ...state.params, [action.id]: { ...defaults } }, outdated: state.trace != null }
    }
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
    case 'saved': // keep the scenario and trace on screen; the new file just becomes the selected one
      return { ...state, scenarios: action.scenarios, scenarioId: action.id }
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
