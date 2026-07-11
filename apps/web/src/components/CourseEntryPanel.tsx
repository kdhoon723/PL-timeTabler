import { PlusIcon } from './Icons'
import type { AcademicProfile } from '../types'

interface Props {
  profile: AcademicProfile | null
  compact?: boolean
  onRequired: () => void
  onEditProfile: () => void
  onSearch: () => void
}

export function CourseEntryPanel({ profile, compact = false, onRequired, onEditProfile, onSearch }: Props) {
  return <section className={`course-entry-panel ${compact ? 'compact' : ''}`} aria-label="과목 찾기">
    {!compact && <div className="section-heading"><div><h2>과목</h2><p>검색해서 시간표에 바로 배치하세요.</p></div></div>}
    <button type="button" className="primary-button full-button course-search-action" onClick={onSearch}><PlusIcon />과목 찾기</button>
    {profile
      ? <button type="button" className="required-guidance" aria-label="필수과목 확인" onClick={onRequired}><span><strong>필수과목 확인</strong><small>{profile.department} · {profile.currentGrade}학년 기준</small></span><span aria-hidden="true">›</span></button>
      : <button type="button" className="profile-guidance" aria-label="학과를 설정하면 필수과목을 안내해요" onClick={onEditProfile}>학과를 설정하면 필수과목을 안내해요 <span aria-hidden="true">›</span></button>}
  </section>
}
