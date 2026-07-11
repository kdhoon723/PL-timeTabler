import { PlusIcon } from './Icons'

interface Props {
  hasProfile: boolean
  compact?: boolean
  onRequired: () => void
  onMajor: () => void
  onLiberal: () => void
  onAll: () => void
}

export function CourseEntryPanel({ hasProfile, compact = false, onRequired, onMajor, onLiberal, onAll }: Props) {
  return <section className={`course-entry-panel ${compact ? 'compact' : ''}`} aria-label="과목 찾기">
    {!compact && <div className="section-heading"><div><h2>과목</h2><p>필수 추천이나 원하는 분류에서 시작하세요.</p></div></div>}
    <button type="button" className="primary-button full-button" onClick={onAll}><PlusIcon />전체 과목 추가</button>
    <div className="course-entry-shortcuts">
      <button type="button" onClick={onRequired}>필수 추천</button>
      <button type="button" onClick={onMajor}>{hasProfile ? '내 전공' : '학과 설정'}</button>
      <button type="button" onClick={onLiberal}>교양</button>
    </div>
  </section>
}
