/** North arrow for a view rotated by `rot` rad (see lib/mapProjection.js): it points to where world north is on screen. */
export default function NorthArrow({ rot }) {
  const R = 20 // arrow length in px
  const phi = -rot // north is rotated by -rot, clockwise from "up" on screen
  const label = [18 + (R + 8) * Math.sin(phi), 20 - (R + 8) * Math.cos(phi)] // the N stays upright, beyond the tip
  return (
    <svg width={36} height={40} aria-label="North arrow">
      <g transform={`translate(18 20) rotate(${(phi * 180) / Math.PI})`}>
        <path d={`M0 ${-R * 0.8} L5 6 L0 2 L-5 6 Z`} fill="#374151" />
      </g>
      <text x={label[0]} y={label[1]} fontSize={11} fontWeight={600} fill="#374151" textAnchor="middle" dominantBaseline="middle">N</text>
    </svg>
  )
}
