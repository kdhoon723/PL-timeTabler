import { useEffect, useRef } from 'react'
import type { CourseRole, Section } from '../types'
import { formatSession } from '../domain/time'
import { CloseIcon, TrashIcon } from './Icons'
import { useSheetSwipeDismiss } from '../hooks/useSheetSwipeDismiss'

type AdjustmentMode = 'AUTO' | 'PROFESSOR' | 'SECTION'

interface Props {
  section: Section | null
  role: CourseRole
  locked: boolean
  professorLocked: boolean
  professorLockAvailable: boolean
  alternatives: Section[]
  onClose: () => void
  onRole: (role: CourseRole) => void
  onAdjustmentMode: (mode: AdjustmentMode) => void
  onRemove: () => void
  onSwap: (section: Section) => void
}

const ROLE_LABELS: Record<CourseRole, string> = { must: '꼭 포함', want: '가능하면', backup: '예비', exclude: '제외' }
const ROLE_HELP: Record<CourseRole, string> = {
  must: '과목은 넣고 분반은 조건에 맞춰요.',
  want: '조건에 맞으면 시간표에 넣어요.',
  backup: '현재 시간표에서는 빼고 후보로만 써요.',
  exclude: '이 과목의 모든 분반을 빼요.',
}

export function SectionDetailSheet({ section, role, locked, professorLocked, professorLockAvailable, alternatives, onClose, onRole, onAdjustmentMode, onRemove, onSwap }: Props) {
  const ref = useRef<HTMLDialogElement>(null)
  const sheetDrag = useSheetSwipeDismiss(ref, onClose)
  useEffect(() => {
    if (section && ref.current && !ref.current.open) ref.current.showModal()
    if (!section && ref.current?.open) ref.current.close()
  }, [section])
  if (!section) return <dialog ref={ref} />
  const adjustmentMode: AdjustmentMode = locked ? 'SECTION' : professorLocked ? 'PROFESSOR' : 'AUTO'
  const shownAlternatives = professorLocked ? alternatives.filter((candidate) => candidate.professor === section.professor) : alternatives
  const adjustmentHelp = adjustmentMode === 'SECTION'
    ? '이 교수·시간·분반을 그대로 유지해요.'
    : adjustmentMode === 'PROFESSOR'
      ? `${section.professor} 교수님의 분반 안에서 시간을 맞춰요.`
      : '교수와 시간을 조건에 맞춰 바꿀 수 있어요.'
  return <dialog className="sheet detail-sheet" ref={ref} onClose={onClose} onCancel={(event) => { event.preventDefault(); onClose() }} aria-labelledby="detail-title">
    <div className="sheet-header" {...sheetDrag}><div><h2 id="detail-title">{section.name}</h2><p>{section.courseCode}-{section.sectionCode} · {section.credits}학점</p></div><button type="button" className="icon-button" onClick={onClose} aria-label="과목 상세 닫기"><CloseIcon /></button></div>
    <dl className="detail-list"><div><dt>담당 교수</dt><dd>{section.professor ?? '미정'}</dd></div><div><dt>이수 구분</dt><dd>{section.category}</dd></div><div><dt>수업</dt><dd>{section.sessions.length ? section.sessions.map(formatSession).join(', ') : '시간 미정 — 충돌 여부를 직접 확인하세요'}</dd></div></dl>
    <fieldset className="role-fieldset"><legend>자동 생성 기준</legend><div>{(Object.keys(ROLE_LABELS) as CourseRole[]).map((value) => <label key={value} className={role === value ? 'checked' : ''}><input type="radio" name="course-role" value={value} checked={role === value} onChange={() => onRole(value)} />{ROLE_LABELS[value]}</label>)}</div><p aria-live="polite">{ROLE_HELP[role]}</p></fieldset>
    {(role === 'must' || role === 'want') && <fieldset className="adjustment-fieldset"><legend>자동 조정 범위</legend><div>
      <label className={adjustmentMode === 'AUTO' ? 'checked' : ''}><input type="radio" name="adjustment-mode" checked={adjustmentMode === 'AUTO'} onChange={() => onAdjustmentMode('AUTO')} />자동</label>
      {(professorLockAvailable || professorLocked) && <label className={adjustmentMode === 'PROFESSOR' ? 'checked' : ''}><input type="radio" name="adjustment-mode" checked={adjustmentMode === 'PROFESSOR'} onChange={() => onAdjustmentMode('PROFESSOR')} />교수 유지</label>}
      <label className={adjustmentMode === 'SECTION' ? 'checked' : ''}><input type="radio" name="adjustment-mode" checked={adjustmentMode === 'SECTION'} onChange={() => onAdjustmentMode('SECTION')} />현재 수업</label>
    </div><p aria-live="polite">{adjustmentHelp}</p></fieldset>}
    <div className="detail-actions"><button type="button" className="danger-button" onClick={onRemove}><TrashIcon />과목 삭제</button></div>
    <section className="alternative-section"><h3>{professorLocked ? '같은 교수님의 다른 분반' : '충돌 없는 다른 분반'}</h3>{shownAlternatives.length ? <div className="alternative-list">{shownAlternatives.slice(0, 8).map((candidate) => <button type="button" key={candidate.id} onClick={() => onSwap(candidate)}><span><strong>{candidate.sectionCode}분반 · {candidate.professor ?? '교수 미정'}</strong><small>{candidate.sessions.map(formatSession).join(' / ') || '시간 미정'}</small></span><span>교체</span></button>)}</div> : <p className="muted-copy">현재 선택과 충돌하지 않는 다른 분반이 없습니다.</p>}</section>
  </dialog>
}
