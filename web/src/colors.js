export const TRUTH_COLOR = '#111827'

const PALETTE = ['#2563eb', '#dc2626', '#059669', '#d97706', '#7c3aed', '#0891b2', '#db2777']

/** Fixed color per estimator, assigned in registry order. */
export function estimatorColor(estimators, id) {
  const i = estimators.findIndex((e) => e.id === id)
  return PALETTE[(i < 0 ? 0 : i) % PALETTE.length]
}
