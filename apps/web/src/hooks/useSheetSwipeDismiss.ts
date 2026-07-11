import { useCallback, useRef } from 'react'
import type { PointerEventHandler, RefObject } from 'react'

const DISMISS_DISTANCE = 72

interface DragState {
  pointerId: number
  startY: number
  distance: number
}

export function useSheetSwipeDismiss(dialogRef: RefObject<HTMLDialogElement | null>, onDismiss: () => void) {
  const drag = useRef<DragState | null>(null)

  const reset = useCallback(() => {
    drag.current = null
    const dialog = dialogRef.current
    dialog?.classList.remove('sheet-dragging')
    dialog?.style.removeProperty('--sheet-drag-y')
  }, [dialogRef])

  const onPointerDown: PointerEventHandler<HTMLDivElement> = useCallback((event) => {
    if (event.pointerType === 'mouse' || event.button > 0) return
    drag.current = { pointerId: event.pointerId, startY: event.clientY, distance: 0 }
    dialogRef.current?.classList.add('sheet-dragging')
    event.currentTarget.setPointerCapture?.(event.pointerId)
  }, [dialogRef])

  const onPointerMove: PointerEventHandler<HTMLDivElement> = useCallback((event) => {
    const current = drag.current
    if (!current || current.pointerId !== event.pointerId) return
    current.distance = Math.max(0, event.clientY - current.startY)
    dialogRef.current?.style.setProperty('--sheet-drag-y', `${Math.min(current.distance, 240)}px`)
    if (current.distance > 0) event.preventDefault()
  }, [dialogRef])

  const finish: PointerEventHandler<HTMLDivElement> = useCallback((event) => {
    const current = drag.current
    if (!current || current.pointerId !== event.pointerId) return
    const dismiss = current.distance >= DISMISS_DISTANCE
    event.currentTarget.releasePointerCapture?.(event.pointerId)
    reset()
    if (dismiss) onDismiss()
  }, [onDismiss, reset])

  return { onPointerDown, onPointerMove, onPointerUp: finish, onPointerCancel: reset }
}
