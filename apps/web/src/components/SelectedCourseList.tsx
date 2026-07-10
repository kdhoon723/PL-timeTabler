import type { PlanItem, Section } from '../types'
import { formatSession } from '../domain/time'
import { LockIcon } from './Icons'

interface Props {
  items: PlanItem[]
  sectionById: Map<string, Section>
  onSelect: (section: Section) => void
}

const ROLE_LABEL = { must: '반드시', want: '희망', backup: '예비', exclude: '제외' }

export function SelectedCourseList({ items, sectionById, onSelect }: Props) {
  const entries = items.map((item) => ({ item, section: sectionById.get(item.sectionId) })).filter((entry): entry is { item: PlanItem; section: Section } => !!entry.section)
  return <section className="selected-section" aria-labelledby="selected-title">
    <div className="section-heading"><div><h2 id="selected-title">선택한 과목</h2><p>과목을 눌러 분반과 역할을 바꿀 수 있습니다.</p></div><span>{entries.length}개</span></div>
    {entries.length === 0 ? <p className="empty-copy">아직 선택한 과목이 없습니다.</p> : <ul className="selected-list">
      {entries.map(({ item, section }) => <li key={section.id}><button type="button" onClick={() => onSelect(section)}>
        <span className={`role-mark role-${item.role}`}>{ROLE_LABEL[item.role]}</span>
        <span className="selected-main"><strong>{section.name}</strong><small>{section.sectionCode}분반 · {section.professor ?? '교수 미정'} · {section.sessions.map(formatSession).join(' / ') || '시간 미정'}</small></span>
        {item.locked && <span className="lock-label"><LockIcon />잠김</span>}
      </button></li>)}
    </ul>}
  </section>
}
