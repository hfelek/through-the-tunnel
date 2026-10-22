import { useEffect } from 'react'

/** Modal with a title and a text; closed by the button, Escape or a click outside the box. */
export default function InfoModal({ title, text, onClose }) {
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" role="dialog" aria-modal="true" aria-label={title} onClick={(e) => e.stopPropagation()}>
        <h2>{title}</h2>
        <p>{text}</p>
        <button className="modal-close" onClick={onClose} autoFocus>Close</button>
      </div>
    </div>
  )
}
