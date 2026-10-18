import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react'
import { getEstimators, getPresets, getScenario, getScenarios, saveScenario, simulate } from './api'
import { initialState, reducer } from './state'
import Toolbar from './components/Toolbar'
import Panel from './components/Panel'
import Controls from './components/Controls'
import EstimatorPicker from './components/EstimatorPicker'
import MetricsTable from './components/MetricsTable'
import JsonEditor from './components/JsonEditor'
import ErrorBoundary from './components/ErrorBoundary'
import ElevationProfile from './components/ElevationProfile'
import MapView from './components/MapView'
import Timeline from './components/Timeline'
import ChartStack from './components/ChartStack'
import ErrorChart from './components/ErrorChart'
import SensorCharts from './components/SensorCharts'
import { vehicleDuration } from './lib/trace'
import { usePlayback } from './lib/usePlayback'

export default function App() {
  const [state, dispatch] = useReducer(reducer, initialState)
  const duration = useMemo(() => vehicleDuration(state.trace?.vehicles?.[0]), [state.trace])
  // playback time lives outside the reducer so moving it never rebuilds the trace
  const { t, playing, speed, setSpeed, seek, toggle } = usePlayback(duration, state.trace)
  const fail = (e) => dispatch({ type: 'error', message: e.message })

  useEffect(() => {
    getPresets().then((presets) => dispatch({ type: 'presets_loaded', presets }), fail)
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
  // the latest state for handlers that fire after a render (slider release, auto-run)
  const latest = useRef(state)
  useEffect(() => { latest.current = state })
  const runSeq = useRef(0)
  const runWith = useCallback((scenario) => {
    const { selected, params, calloutK } = latest.current
    const runId = ++runSeq.current
    dispatch({ type: 'run_start', runId })
    const chosen = Object.fromEntries(selected.map((id) => [id, params[id] ?? {}]))
    simulate(scenario, chosen, 10, calloutK).then(
      (trace) => dispatch({ type: 'run_done', runId, trace }),
      (e) => dispatch({ type: 'run_failed', runId, message: e.message }),
    )
  }, [])
  const run = useCallback(() => runWith(latest.current.scenario), [runWith])
  // an edit action: apply it now (the ref sees it before the next render); run too when it is a commit and auto-run is on
  const applyEdit = useCallback((action, commit) => {
    latest.current = reducer(latest.current, action)
    dispatch(action)
    if (commit && latest.current.autoRun) runWith(latest.current.scenario)
  }, [runWith])
  const edit = useCallback((scenario, commit) => applyEdit({ type: 'edit_scenario', scenario }, commit), [applyEdit])
  const commit = useCallback(() => { if (latest.current.autoRun) runWith(latest.current.scenario) }, [runWith])
  const setCalloutK = useCallback((value) => applyEdit({ type: 'set_callout_k', value }, false), [applyEdit])
  const setAutoRun = useCallback((value) => dispatch({ type: 'set_auto_run', value }), [])
  const toggleEstimator = useCallback((id) => applyEdit({ type: 'toggle_estimator', id }, true), [applyEdit])
  const setParam = useCallback((id, name, value) => applyEdit({ type: 'set_param', id, name, value }, true), [applyEdit])
  const resetParams = useCallback((id) => applyEdit({ type: 'reset_params', id }, true), [applyEdit])
  const resetToSaved = useCallback(() => {
    const id = latest.current.scenarioId
    if (id) getScenario(id).then((scenario) => edit(scenario, true), fail)
  }, [edit])

  const [editing, setEditing] = useState(false)
  const openEditor = useCallback(() => setEditing(true), [])
  const applyJson = useCallback((scenario) => { setEditing(false); edit(scenario, true) }, [edit])
  const closeEditor = useCallback(() => setEditing(false), [])
  const save = useCallback(async (id, scenario) => {
    await saveScenario(id, scenario)
    const scenarios = await getScenarios()
    dispatch({ type: 'saved', id, scenarios })
  }, [])

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
          <ErrorBoundary name="Metrics" resetKey={state.trace}>
            <MetricsTable trace={state.trace} estimators={state.estimators} />
          </ErrorBoundary>
          <ErrorBoundary name="Charts" resetKey={state.trace}>
            <ChartStack duration={duration} t={t} onSeek={seek}>
              {(w) => (
                <>
                  <ErrorBoundary name="Error chart" resetKey={state.trace}>
                    <ErrorChart trace={state.trace} estimators={state.estimators} duration={duration} w={w} />
                  </ErrorBoundary>
                  <ErrorBoundary name="Sensor charts" resetKey={state.trace}>
                    <SensorCharts trace={state.trace} duration={duration} w={w} />
                  </ErrorBoundary>
                </>
              )}
            </ChartStack>
          </ErrorBoundary>
        </div>
        <div className="right">
          <ErrorBoundary name="Controls">
            <Controls
              scenario={state.scenario} presets={state.presets} calloutK={state.calloutK} autoRun={state.autoRun}
              onEdit={edit} onCommit={commit} onCalloutK={setCalloutK} onAutoRun={setAutoRun}
              onEditJson={openEditor} onReset={resetToSaved} onSave={save}
            />
          </ErrorBoundary>
          <ErrorBoundary name="Methods">
            <EstimatorPicker
              estimators={state.estimators} selected={state.selected} params={state.params}
              onToggle={toggleEstimator} onParam={setParam} onReset={resetParams}
            />
          </ErrorBoundary>
          <ErrorBoundary name="Panel" resetKey={state.trace}>
            <Panel trace={state.trace} estimators={state.estimators} outdated={state.outdated} />
          </ErrorBoundary>
        </div>
      </main>
      {editing && state.scenario && <JsonEditor scenario={state.scenario} onApply={applyJson} onClose={closeEditor} />}
    </div>
  )
}
