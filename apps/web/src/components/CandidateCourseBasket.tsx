import type { PlanItem, Section } from '../types'
import { CloseIcon, PlusIcon } from './Icons'

interface Props {
  items: PlanItem[]
  sectionById: Map<string, Section>
  onAdd: () => void
  onPromote: (section: Section) => void
  onRemove: (section: Section) => void
}

function uniqueCourses(items: PlanItem[], sectionById: Map<string, Section>, role: 'backup' | 'exclude') {
  const seen = new Set<string>()
  return items.flatMap((item) => {
    if (item.role !== role) return []
    const section = sectionById.get(item.sectionId)
    if (!section || seen.has(section.courseCode)) return []
    seen.add(section.courseCode)
    return [section]
  })
}

export function CandidateCourseBasket({ items, sectionById, onAdd, onPromote, onRemove }: Props) {
  const candidates = uniqueCourses(items, sectionById, 'backup')
  const excluded = uniqueCourses(items, sectionById, 'exclude')

  return <section className="candidate-basket" aria-labelledby="candidate-basket-title">
    <div className="section-heading">
      <div><h2 id="candidate-basket-title">자동완성 후보</h2><p>시간표에는 놓지 않고 조합할 때만 사용해요.</p></div>
      <span>{candidates.length}개</span>
    </div>
    {candidates.length === 0
      ? <div className="candidate-basket-empty"><p>전공선택이나 교양선택을 후보로 담아두세요.</p><button type="button" className="secondary-button" onClick={onAdd}><PlusIcon />후보 과목 담기</button></div>
      : <><ul className="candidate-basket-list">
        {candidates.map((section) => <li key={section.courseCode}>
          <span className="candidate-basket-main"><strong>{section.name}</strong><small>{section.courseCode} · {section.category} · {section.credits}학점</small></span>
          <span className="candidate-basket-actions"><button type="button" onClick={() => onPromote(section)}>시간표에 넣기</button><button type="button" className="icon-button" aria-label={`${section.name} 후보에서 삭제`} onClick={() => onRemove(section)}><CloseIcon /></button></span>
        </li>)}
      </ul><button type="button" className="candidate-add-more" onClick={onAdd}><PlusIcon />후보 더 담기</button></>}
    {excluded.length > 0 && <details className="excluded-course-list"><summary>자동완성에서 제외한 과목 {excluded.length}개</summary><ul>{excluded.map((section) => <li key={section.courseCode}><span>{section.name}</span><button type="button" aria-label={`${section.name} 제외 해제`} onClick={() => onRemove(section)}>해제</button></li>)}</ul></details>}
  </section>
}
