import { useEffect, useRef } from 'react'
import type { PlanItem, Section } from '../types'
import { CloseIcon } from './Icons'
import { RegistrationChecklist } from './RegistrationChecklist'

interface Props {
  open: boolean
  items: PlanItem[]
  sectionById: Map<string, Section>
  onApplyBackup: (section: Section) => void
  onMessage: (message: string) => void
  onExportPng: () => void
  onExportPdf: () => void
  onClose: () => void
}

export function ApplicationListSheet({ open, items, sectionById, onApplyBackup, onMessage, onExportPng, onExportPdf, onClose }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const active = items.filter((item) => item.role === 'must' || item.role === 'want').map((item) => sectionById.get(item.sectionId)).filter((section): section is Section => !!section)
  const credits = Array.from(new Map(active.map((section) => [section.courseCode, section.credits])).values()).reduce((sum, value) => sum + value, 0)

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    else if (!open && dialog.open) dialog.close()
  }, [open])

  return <dialog ref={dialogRef} className="sheet application-list-sheet" aria-labelledby="application-list-title" onCancel={(event) => { event.preventDefault(); onClose() }}>
    <div className="sheet-header">
      <div><h2 id="application-list-title">신청 목록</h2><p>{active.length}개 과목 · {credits}학점</p></div>
      <button type="button" className="icon-button" onClick={onClose} aria-label="신청 목록 닫기"><CloseIcon /></button>
    </div>
    <div className="application-list-content">
      <RegistrationChecklist items={items} sectionById={sectionById} onApplyBackup={onApplyBackup} onMessage={onMessage} />
      <section className="export-panel" aria-labelledby="application-export-title"><h2 id="application-export-title">저장·출력</h2><div><button type="button" className="secondary-button" onClick={onExportPng}>PNG 저장</button><button type="button" className="secondary-button" onClick={onExportPdf}>인쇄·PDF</button></div></section>
    </div>
  </dialog>
}
