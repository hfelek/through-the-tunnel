import { useEffect, useState } from 'react'

export default function App() {
  const [health, setHealth] = useState('...')

  useEffect(() => {
    fetch('/api/health')
      .then((r) => r.json())
      .then((d) => setHealth(d.status))
      .catch(() => setHealth('unreachable'))
  }, [])

  return (
    <div style={{ padding: 24 }}>
      <h1>Through the Tunnel</h1>
      <p>API health: {health}</p>
    </div>
  )
}
