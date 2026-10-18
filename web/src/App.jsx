import { useCallback, useEffect, useMemo, useReducer } from 'react'
import { getEstimators, getScenario, getScenarios, simulate } from './api'
import { initialState, reducer } from './state'
import Toolbar from './components/Toolbar'
import Panel from './components/Panel'
import ErrorBoundary from './components/ErrorBoundary'
import ElevationProfile from './components/ElevationProfile'
import MapView from './components/MapView'
import Timeline from './components/Timeline'
import { Charts } from './components/Placeholders'
import { vehicleDuration } from './lib/trace'
import { usePlayback } from './lib/usePlayback'

export default function App() {
  const [state, dispatch] = useReducer(reducer, initialState)
  const duration = useMemo(() => vehicleDuration(state.trace?.vehicles?.[0]), [state.trace])
  // playback time lives outside the reducer so moving it never rebuilds the trace
  const { t, playing, speed, setSpeed, seek, toggle } = usePlayback(duration, state.trace)
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

  const select = useCallback((id) => dispatch({ type: 'select_scenario', id }), [])
  const run = useCallback(() => {
    dispatch({ type: 'run_start' })
    const params = Object.fromEntries(state.estimators.map((e) => [e.id, {}]))
    simulate(state.scenario, params).then(
      (trace) => dispatch({ type: 'run_done', trace }),
      (e) => dispatch({ type: 'run_failed', message: e.message }),
    )
  }, [state.estimators, state.scenario])

  return (
    <div className="app">
      <Toolbar state={state} onSelect={select} onRun={run} />
      <main className="layout">
        <div className="left">
          <ErrorBoundary name="Map" resetKey={state.trace}>
            <MapView trace={state.trace} estimators={state.estimators} t={t} />
          </ErrorBoundary>
          <ErrorBoundary name="Elevation" resetKey={state.trace}>
            <ElevationProfile trace={state.trace} estimators={state.estimators} t={t} />
          </ErrorBoundary>
          <ErrorBoundary name="Timeline" resetKey={state.trace}>
            <Timeline
              trace={state.trace}
              duration={duration}
              t={t}
              playing={playing}
              speed={speed}
              onSeek={seek}
              onToggle={toggle}
              onSpeed={setSpeed}
            />
          </ErrorBoundary>
          <ErrorBoundary name="Charts" resetKey={state.trace}>
            <Charts />
          </ErrorBoundary>
        </div>
        <ErrorBoundary name="Panel" resetKey={state.trace}>
          <Panel trace={state.trace} estimators={state.estimators} />
        </ErrorBoundary>
      </main>
    </div>
  )
}
