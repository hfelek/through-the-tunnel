export const initialState = {
  scenarios: [],
  scenarioId: null,
  scenario: null, // single source of truth for the scenario JSON
  estimators: [],
  trace: null, // replaced as a whole, never mutated
  loading: false,
  error: null,
}

export function reducer(state, action) {
  switch (action.type) {
    case 'scenarios_loaded':
      return { ...state, scenarios: action.scenarios }
    case 'estimators_loaded':
      return { ...state, estimators: action.estimators }
    case 'select_scenario':
      return { ...state, scenarioId: action.id, scenario: null, trace: null, error: null }
    case 'scenario_loaded':
      return action.id === state.scenarioId ? { ...state, scenario: action.scenario } : state
    case 'run_start':
      return { ...state, loading: true, error: null }
    case 'run_done':
      return { ...state, loading: false, trace: action.trace }
    case 'run_failed':
      return { ...state, loading: false, error: action.message }
    case 'error':
      return { ...state, error: action.message }
    default:
      return state
  }
}
