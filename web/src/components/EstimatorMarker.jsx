/** Hollow marker of one estimator at (x, y). `r` is the circle radius; the other shapes are scaled to a similar area. */
export default function EstimatorMarker({ shape, x, y, r, color, strokeWidth = 2.5, strokeOpacity = 1 }) {
  const common = { fill: 'none', stroke: color, strokeWidth, strokeOpacity, strokeLinejoin: 'round' }
  if (shape === 'square') {
    const h = r * 0.9
    return <rect x={x - h} y={y - h} width={2 * h} height={2 * h} {...common} />
  }
  if (shape === 'diamond') {
    const d = r * 1.25
    return <polygon points={`${x},${y - d} ${x + d},${y} ${x},${y + d} ${x - d},${y}`} {...common} />
  }
  if (shape === 'triangle') {
    const R = r * 1.35 // circumradius; the centroid sits at (x, y)
    const pts = [-90, 30, 150].map((deg) => `${x + R * Math.cos((deg * Math.PI) / 180)},${y + R * Math.sin((deg * Math.PI) / 180)}`)
    return <polygon points={pts.join(' ')} {...common} />
  }
  return <circle cx={x} cy={y} r={r} {...common} />
}
