import { useEffect, useReducer } from 'react'
import { getEstimators, getScenario, getScenarios, simulate } from './api'
import { initialState, reducer } from './state'
import Toolbar from './components/Toolbar'
import Panel from './components/Panel'
import { Charts, MapView, Timeline } from './components/Placeholders'

export default function App() {
  const [state, dispatch] = useReducer(reducer, initialState)
  const fail = (e) => dispatch({ type: 'error', message: e.message })

  useEffect(() => {
    getEstimators().then((estimators) => dispatch({ type: 'estimators_loaded', estimators }), fail)
    getScenarios().then((scenarios) => {
      dispatch({ type: 'scenarios_loaded', scenarios })
      if (scenarios.length) dispatch({ type: 'select_scenario', id: scenarios[0].id })
    }, fail)
  }, [])

  useEffect(() => {
    const id = state.scenarioId
    if (!id) return
    getScenario(id).then((scenario) => dispatch({ type: 'scenario_loaded', id, scenario }), fail)
  }, [state.scenarioId])

  const run = () => {
    dispatch({ type: 'run_start' })
    const params = Object.fromEntries(state.estimators.map((e) => [e.id, {}]))
    simulate(state.scenario, params).then(
      (trace) => dispatch({ type: 'run_done', trace }),
      (e) => dispatch({ type: 'run_failed', message: e.message }),
    )
  }

  return (
    <div className="app">
      <Toolbar
        state={state}
        onSelect={(id) => dispatch({ type: 'select_scenario', id })}
        onRun={run}
      />
      <main className="layout">
        <div className="left">
          <MapView />
          <Timeline />
          <Charts />
        </div>
        <Panel trace={state.trace} estimators={state.estimators} />
      </main>
    </div>
  )
}
