import { useEffect, useRef } from 'react'
import type { CourseRole, Section } from '../types'
import { formatSession } from '../domain/time'
import { CloseIcon, LockIcon, TrashIcon, UnlockIcon } from './Icons'

interface Props {
  section: Section | null
  role: CourseRole
  locked: boolean
  alternatives: Section[]
  onClose: () => void
  onRole: (role: CourseRole) => void
  onLock: () => void
  onRemove: () => void
  onSwap: (section: Section) => void
}

const ROLE_LABELS: Record<CourseRole, string> = { must: '반드시', want: '희망', backup: '예비', exclude: '제외' }

export function SectionDetailSheet({ section, role, locked, alternatives, onClose, onRole, onLock, onRemove, onSwap }: Props) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    if (section && ref.current && !ref.current.open) ref.current.showModal()
    if (!section && ref.current?.open) ref.current.close()
  }, [section])
  if (!section) return <dialog ref={ref} />
  return <dialog className="sheet detail-sheet" ref={ref} onClose={onClose} onCancel={(event) => { event.preventDefault(); onClose() }} aria-labelledby="detail-title">
    <div className="sheet-header"><div><h2 id="detail-title">{section.name}</h2><p>{section.courseCode}-{section.sectionCode} · {section.credits}학점</p></div><button type="button" className="icon-button" onClick={onClose} aria-label="과목 상세 닫기"><CloseIcon /></button></div>
    <dl className="detail-list"><div><dt>담당 교수</dt><dd>{section.professor ?? '미정'}</dd></div><div><dt>이수 구분</dt><dd>{section.category}</dd></div><div><dt>수업</dt><dd>{section.sessions.length ? section.sessions.map(formatSession).join(', ') : '시간 미정 — 충돌 여부를 직접 확인하세요'}</dd></div></dl>
    <fieldset className="role-fieldset"><legend>이 과목의 역할</legend><div>{(Object.keys(ROLE_LABELS) as CourseRole[]).map((value) => <label key={value} className={role === value ? 'checked' : ''}><input type="radio" name="course-role" value={value} checked={role === value} onChange={() => onRole(value)} />{ROLE_LABELS[value]}</label>)}</div><p>예비와 제외 과목은 현재 시간표·학점 계산에서 빠집니다.</p></fieldset>
    <div className="detail-actions"><button type="button" className="secondary-button" onClick={onLock}>{locked ? <UnlockIcon /> : <LockIcon />}{locked ? '잠금 해제' : '분반 잠금'}</button><button type="button" className="danger-button" onClick={onRemove}><TrashIcon />삭제</button></div>
    <section className="alternative-section"><h3>충돌 없는 다른 분반</h3>{alternatives.length ? <div className="alternative-list">{alternatives.slice(0, 8).map((candidate) => <button type="button" key={candidate.id} onClick={() => onSwap(candidate)}><span><strong>{candidate.sectionCode}분반 · {candidate.professor ?? '교수 미정'}</strong><small>{candidate.sessions.map(formatSession).join(' / ') || '시간 미정'}</small></span><span>교체</span></button>)}</div> : <p className="muted-copy">현재 선택과 충돌하지 않는 다른 분반이 없습니다.</p>}</section>
  </dialog>
}
