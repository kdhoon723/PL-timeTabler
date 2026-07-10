import type { RefObject } from 'react'
import type { CandidateDiff } from '../domain/candidateDiff'
import type { Candidate } from '../types'

interface Props {
  candidate: Candidate
  diff: CandidateDiff
  containerRef: RefObject<HTMLElement | null>
  onApply: () => void
  onCancel: () => void
}

export function CandidatePreviewBar({ candidate, diff, containerRef, onApply, onCancel }: Props) {
  const changes = [
    ...diff.swaps.map(({ from, to }) => ({ key: `swap-${from.id}-${to.id}`, text: `교체: ${from.name} ${from.sectionCode}분반 → ${to.sectionCode}분반` })),
    ...diff.added.map((section) => ({ key: `add-${section.id}`, text: `추가: ${section.name} ${section.sectionCode}분반` })),
    ...diff.removed.map((section) => ({ key: `remove-${section.id}`, text: `제외: ${section.name} ${section.sectionCode}분반` })),
  ]

  return <section className="preview-comparison" ref={containerRef} tabIndex={-1} aria-labelledby="preview-title">
    <div className="preview-comparison-heading">
      <div><span className="preview-eyebrow">저장 전 미리보기</span><h2 id="preview-title">후보 {candidate.rank} 변경 내용</h2></div>
      <p>{diff.kept.length}개 유지 · {diff.swaps.length}개 교체 · {diff.added.length}개 추가 · {diff.removed.length}개 제외</p>
    </div>
    <dl className="preview-metrics" aria-label="후보 시간표 요약">
      <div><dt>등교일</dt><dd>{candidate.metrics.campusDays}일</dd></div>
      <div><dt>학점</dt><dd>{candidate.metrics.credits}학점</dd></div>
      <div><dt>빈 시간</dt><dd>{candidate.metrics.totalGapMinutes}분</dd></div>
      <div><dt>첫 수업</dt><dd>{candidate.metrics.earliest ?? '없음'}</dd></div>
      <div><dt>마지막 수업</dt><dd>{candidate.metrics.latest ?? '없음'}</dd></div>
    </dl>
    {changes.length ? <ul className="preview-change-list">{changes.map((change) => <li key={change.key}>{change.text}</li>)}</ul> : <p className="preview-no-changes">현재 시간표와 같은 구성입니다.</p>}
    <div className="preview-actions">
      <button type="button" className="secondary-button" onClick={onCancel}>미리보기 취소</button>
      <button type="button" className="primary-button" onClick={onApply}>후보 적용</button>
    </div>
  </section>
}
