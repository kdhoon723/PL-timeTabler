import { useEffect, useState } from 'react'
import { cancelOptimizationJob, createOptimizationJob, getOptimizationJob } from '../api/client'
import type { Candidate, DraftSnapshot, OptimizationJob } from '../types'
import { CheckIcon, SlidersIcon } from './Icons'

interface Props { draft: DraftSnapshot; onApply: (candidate: Candidate) => void }
const DONE = new Set(['SUCCEEDED', 'INFEASIBLE', 'TIME_LIMIT', 'CANCELLED', 'FAILED'])

export function OptimizerPanel({ draft, onApply }: Props) {
  const [job, setJob] = useState<OptimizationJob | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!job || DONE.has(job.status)) return
    const timer = window.setTimeout(async () => {
      try { setJob(await getOptimizationJob(job.id)) }
      catch { setError('자동 생성 상태를 확인하지 못했습니다. 잠시 후 다시 시도해 주세요.') }
    }, 900)
    return () => window.clearTimeout(timer)
  }, [job])

  const generate = async () => {
    setBusy(true); setError(null)
    try { setJob(await createOptimizationJob(draft)) }
    catch { setError('자동 생성 서버에 연결하지 못했습니다. 수동 편집 내용은 그대로 보존됩니다.') }
    finally { setBusy(false) }
  }
  const cancel = async () => {
    if (!job) return
    try { await cancelOptimizationJob(job.id); setJob({ ...job, status: 'CANCELLED' }) } catch { setError('취소 요청을 처리하지 못했습니다.') }
  }

  return <section className="optimizer-panel" aria-labelledby="optimizer-title">
    <div className="section-heading"><div><h2 id="optimizer-title">조건에 맞는 시간표</h2><p>잠근 분반과 필수 과목을 유지해 서로 다른 후보를 만듭니다.</p></div></div>
    {!job && <button type="button" className="primary-button full-button" onClick={generate} disabled={busy}><SlidersIcon />{busy ? '요청 중…' : '시간표 3개 만들기'}</button>}
    {job && !DONE.has(job.status) && <div className="job-status" role="status"><span className="spinner" aria-hidden="true"/><div><strong>{job.status === 'QUEUED' ? '대기 중' : '후보 생성 중'}</strong><p>가짜 진행률 없이 실제 작업 상태만 표시합니다.</p></div><button type="button" onClick={cancel}>취소</button></div>}
    {error && <div className="inline-error" role="alert">{error}</div>}
    {job?.status === 'INFEASIBLE' && <div className="infeasible" role="alert"><strong>모든 조건을 동시에 만족하는 시간표가 없습니다.</strong><ul>{job.relaxationSuggestions.map((suggestion) => <li key={suggestion}>{suggestion}</li>)}</ul><button type="button" className="secondary-button" onClick={generate}>조건을 바꾼 뒤 다시 생성</button></div>}
    {job?.status === 'TIME_LIMIT' && !job.candidates.length && <div className="inline-error">제한 시간 안에 후보를 찾지 못했습니다. 후보 과목 수를 줄이거나 조건을 완화해 주세요.</div>}
    {!!job?.candidates.length && <div className="candidate-list" aria-label="자동 생성 후보">
      {job.candidates.slice(0, 3).map((candidate, index) => <article className="candidate" key={candidate.id}>
        <div className="candidate-heading"><div><span>후보 {index + 1}</span><h3>{candidate.metrics.campusDays}일 등교 · {candidate.metrics.credits}학점</h3></div><strong>{candidate.metrics.totalGapMinutes}분 공강</strong></div>
        <dl><div><dt>첫 수업</dt><dd>{candidate.metrics.earliest ?? '없음'}</dd></div><div><dt>마지막 수업</dt><dd>{candidate.metrics.latest ?? '없음'}</dd></div></dl>
        <ul className="reason-list">{candidate.reasons.slice(0, 3).map((reason) => <li key={reason}><CheckIcon />{reason}</li>)}</ul>
        {!!candidate.unmetPreferences.length && <p className="unmet">미반영: {candidate.unmetPreferences.join(', ')}</p>}
        <button type="button" className={index === 0 ? 'primary-button' : 'secondary-button'} onClick={() => onApply(candidate)}>이 후보 적용</button>
      </article>)}
    </div>}
    {job && DONE.has(job.status) && <button type="button" className="text-button" onClick={generate}>새 조건으로 다시 만들기</button>}
  </section>
}
