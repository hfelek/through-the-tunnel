import { useCallback, useEffect, useRef, useState } from 'react'

const MAX_FRAME_S = 0.1 // a hidden tab pauses rAF; never jump further than this per frame
export const SPEEDS = [1, 2, 5, 10, 20]

/** Playback state for the shared time cursor: t, play/pause, speed, seek and keyboard shortcuts. */
export function usePlayback(duration, trace) {
  const [t, setT] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(5)
  // the rAF loop and key handler read these, so scrubbing mid-play continues from the scrubbed t
  const tRef = useRef(0)
  const speedRef = useRef(speed)
  const durRef = useRef(duration)
  const playingRef = useRef(false)
  useEffect(() => {
    speedRef.current = speed
    durRef.current = duration
    playingRef.current = playing
    tRef.current = t
  })

  const seek = useCallback((v) => {
    const c = Math.min(Math.max(v, 0), durRef.current ?? 0)
    tRef.current = c
    setT(c)
  }, [])

  // a new trace (or a cleared one after a scenario switch) pauses and rewinds
  const [prevTrace, setPrevTrace] = useState(trace)
  if (trace !== prevTrace) {
    setPrevTrace(trace)
    setPlaying(false)
    setT(0)
  }

  useEffect(() => {
    if (!playing) return
    let last = performance.now()
    let raf
    const tick = (now) => {
      const dt = Math.min(Math.max((now - last) / 1000, 0), MAX_FRAME_S)
      last = now
      const end = durRef.current ?? 0
      const next = tRef.current + dt * speedRef.current
      if (next >= end) {
        seek(end)
        setPlaying(false)
        return
      }
      seek(next)
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [playing, seek])

  const toggle = useCallback(() => {
    if (!durRef.current) return
    if (playingRef.current) {
      setPlaying(false)
      return
    }
    if (tRef.current >= durRef.current - 1e-6) seek(0)
    setPlaying(true)
  }, [seek])

  useEffect(() => {
    const onKey = (e) => {
      if (e.ctrlKey || e.metaKey || e.altKey) return
      const el = e.target
      const tag = el.tagName
      if (tag === 'TEXTAREA' || tag === 'SELECT' || el.isContentEditable) return
      if (tag === 'INPUT' && el.type !== 'range') return
      if (e.code === 'Space') {
        if (tag === 'BUTTON') return // the browser already clicks a focused button
        e.preventDefault()
        toggle()
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        e.preventDefault()
        const step = (e.shiftKey ? 10 : 1) * (e.key === 'ArrowLeft' ? -1 : 1)
        seek(tRef.current + step)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [seek, toggle])

  return { t, playing, speed, setSpeed, seek, toggle }
}
