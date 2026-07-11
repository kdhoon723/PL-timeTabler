import type { PlanItem, Section } from '../types'
import { formatSession } from '../domain/time'
import { LockIcon } from './Icons'

interface Props {
  items: PlanItem[]
  sectionById: Map<string, Section>
  onSelect: (section: Section) => void
}

const ROLE_LABEL = { must: '꼭 포함', want: '조정 가능' }

export function SelectedCourseList({ items, sectionById, onSelect }: Props) {
  const entries = items.filter((item) => item.role === 'must' || item.role === 'want').map((item) => ({ item, section: sectionById.get(item.sectionId) })).filter((entry): entry is { item: PlanItem & { role: 'must' | 'want' }; section: Section } => !!entry.section)
  return <section className="selected-section" aria-labelledby="selected-title">
    <div className="section-heading"><div><h2 id="selected-title">현재 시간표</h2><p>격자에 놓인 과목과 자동 조정 범위입니다.</p></div><span>{entries.length}개</span></div>
    {entries.length === 0 ? <p className="empty-copy">아직 시간표에 놓인 과목이 없습니다.</p> : <ul className="selected-list">
      {entries.map(({ item, section }) => <li key={section.id}><button type="button" onClick={() => onSelect(section)}>
        <span className={`role-mark role-${item.role}`}>{ROLE_LABEL[item.role]}</span>
        <span className="selected-main"><strong>{section.name}</strong><small>{section.sectionCode}분반 · {section.professor ?? '교수 미정'} · {section.sessions.map(formatSession).join(' / ') || '시간 미정'}</small></span>
        {(item.locked || item.professorLocked) && <span className="lock-label"><LockIcon />{item.locked ? '수업 유지' : '교수 유지'}</span>}
      </button></li>)}
    </ul>}
  </section>
}
