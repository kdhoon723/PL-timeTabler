import { useEffect, useRef } from 'react'
import type { AcademicProfile, CommonRules, MajorRequiredCourses, PlanItem, Section } from '../types'
import { CloseIcon } from './Icons'
import { RequiredCoursePanel } from './RequiredCoursePanel'
import { useSheetSwipeDismiss } from '../hooks/useSheetSwipeDismiss'

interface Props {
  open: boolean
  profile: AcademicProfile | null
  rules: CommonRules | null
  majorRequired: MajorRequiredCourses | null
  catalog: Section[]
  items: PlanItem[]
  sectionById: ReadonlyMap<string, Section>
  onClose: () => void
  onEditProfile: () => void
  onAddRequired: (section: Section) => void
  onBrowseMajor: () => void
  onBrowseLiberal: () => void
}

export function RequiredCourseSheet({ open, profile, rules, majorRequired, catalog, items, sectionById, onClose, onEditProfile, onAddRequired, onBrowseMajor, onBrowseLiberal }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const sheetDrag = useSheetSwipeDismiss(dialogRef, onClose)
  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    else if (!open && dialog.open) dialog.close()
  }, [open])

  return <dialog ref={dialogRef} className="sheet required-course-sheet" aria-labelledby="required-course-sheet-title" onCancel={(event) => { event.preventDefault(); onClose() }}>
    <div className="sheet-header" {...sheetDrag}><div><h2 id="required-course-sheet-title">필수과목 확인</h2><p>확인된 필수과목만 분반과 함께 보여드려요.</p></div><button type="button" className="icon-button" onClick={onClose} aria-label="필수과목 확인 닫기"><CloseIcon /></button></div>
    <RequiredCoursePanel profile={profile} rules={rules} majorRequired={majorRequired} catalog={catalog} items={items} sectionById={sectionById} onEditProfile={onEditProfile} onAddRequired={onAddRequired} onBrowseMajor={onBrowseMajor} onBrowseLiberal={onBrowseLiberal} initiallyExpanded />
  </dialog>
}
