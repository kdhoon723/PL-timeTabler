import { useEffect } from 'react'

export function Toast({ message, onClose, onUndo }: { message: string | null; onClose: () => void; onUndo?: () => void }) {
  useEffect(() => {
    if (!message) return
    const timer = window.setTimeout(onClose, 4500)
    return () => window.clearTimeout(timer)
  }, [message, onClose])
  if (!message) return null
  return <div className="toast" role="status"><span>{message}</span>{onUndo && <button type="button" onClick={onUndo}>되돌리기</button>}</div>
}
