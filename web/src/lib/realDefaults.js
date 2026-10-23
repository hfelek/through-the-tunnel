/** The registry entries with a recording's default_params applied to the methods that have those parameters (T10.6c). */
export function withRealDefaults(estimators, recording) {
  const overrides = recording?.default_params ?? {}
  return estimators.map((e) => ({
    ...e,
    params: { ...e.params, ...Object.fromEntries(Object.entries(overrides).filter(([name]) => name in e.params)) },
  }))
}

/** Parameter values per method id, starting at those defaults. */
export function realParamsFor(estimators, recording) {
  return Object.fromEntries(withRealDefaults(estimators, recording).map((e) => [e.id, { ...e.params }]))
}
