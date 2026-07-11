import { useEffect, useRef, useState } from 'react'
import { cancelOptimizationJob, createOptimizationJob, getOptimizationJob } from '../api/client'
import { diffCandidate } from '../domain/candidateDiff'
import type { Candidate, DraftSnapshot, OptimizationJob, Section } from '../types'
import { CheckIcon, SlidersIcon } from './Icons'

interface Props {
  draft: DraftSnapshot
  draftFingerprint: string
  sections: readonly Section[]
  onPreview: (candidate: Candidate, generationFingerprint: string) => void
}
const DONE = new Set(['SUCCEEDED', 'INFEASIBLE', 'TIME_LIMIT', 'CANCELLED', 'FAILED'])
const STALE_NOTICE = '시간표 조건이 바뀌어 이전 후보를 지웠습니다. 새 후보를 다시 만들어 주세요.'

export function OptimizerPanel({ draft, draftFingerprint, sections, onPreview }: Props) {
  const [generation, setGeneration] = useState<{ job: OptimizationJob; fingerprint: string } | null>(null)
  const [pendingFingerprint, setPendingFingerprint] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [staleNotice, setStaleNotice] = useState<string | null>(null)
  const currentFingerprintRef = useRef(draftFingerprint)
  const requestSequenceRef = useRef(0)
  currentFingerprintRef.current = draftFingerprint
  const job = generation && generation.fingerprint === draftFingerprint ? generation.job : null
  const sectionById = new Map(sections.map((section) => [section.id, section]))
  const availableCredits = new Map<string, number>()
  for (const item of draft.items) {
    const section = sectionById.get(item.sectionId)
    if (item.role !== 'exclude' && section) availableCredits.set(section.courseCode, section.credits)
  }
  const candidateCredits = [...availableCredits.values()].reduce<number>((sum, credits) => sum + credits, 0)
  const canGenerate = !!draft.dataVersion && candidateCredits >= draft.preferences.minCredits
  const activeJobId = job && !DONE.has(job.status) ? job.id : null
  const activeJobFingerprint = activeJobId ? generation?.fingerprint ?? null : null

  useEffect(() => {
    const staleGeneration = generation && generation.fingerprint !== draftFingerprint ? generation : null
    const staleRequest = pendingFingerprint && pendingFingerprint !== draftFingerprint
    if (!staleGeneration && !staleRequest) return
    requestSequenceRef.current += 1
    if (staleGeneration && !DONE.has(staleGeneration.job.status)) void cancelOptimizationJob(staleGeneration.job.id).catch(() => undefined)
    setGeneration(null)
    setPendingFingerprint(null)
    setBusy(false)
    setError(null)
    setStaleNotice(STALE_NOTICE)
  }, [draftFingerprint, generation, pendingFingerprint])

  useEffect(() => {
    if (!activeJobId || !activeJobFingerprint) return
    const controller = new AbortController()
    let timer: number | undefined
    let failures = 0
    const poll = async () => {
      try {
        const next = await getOptimizationJob(activeJobId, controller.signal)
        if (controller.signal.aborted || currentFingerprintRef.current !== activeJobFingerprint) return
        failures = 0
        setError(null)
        setGeneration((current) => current?.job.id === activeJobId && current.fingerprint === activeJobFingerprint ? { job: next, fingerprint: activeJobFingerprint } : current)
        if (DONE.has(next.status)) return
      } catch (error) {
        if (controller.signal.aborted || error instanceof DOMException && error.name === 'AbortError') return
        failures += 1
        setError('자동 생성 상태 연결이 잠시 끊겼습니다. 자동으로 다시 확인합니다.')
      }
      const delay = Math.min(900 * 2 ** failures, 5_000)
      timer = window.setTimeout(poll, delay)
    }
    timer = window.setTimeout(poll, 900)
    return () => { controller.abort(); if (timer !== undefined) window.clearTimeout(timer) }
  }, [activeJobFingerprint, activeJobId])

  const generate = async () => {
    const fingerprint = draftFingerprint
    const requestSequence = ++requestSequenceRef.current
    setBusy(true); setError(null); setStaleNotice(null); setGeneration(null); setPendingFingerprint(fingerprint)
    try {
      const next = await createOptimizationJob(draft, sections)
      if (requestSequenceRef.current !== requestSequence || currentFingerprintRef.current !== fingerprint) return
      setGeneration({ job: next, fingerprint })
    } catch {
      if (requestSequenceRef.current === requestSequence && currentFingerprintRef.current === fingerprint) setError('자동 생성 서버에 연결하지 못했습니다. 수동 편집 내용은 그대로 보존됩니다.')
    } finally {
      if (requestSequenceRef.current === requestSequence) {
        setBusy(false)
        setPendingFingerprint(null)
      }
    }
  }
  const cancel = async () => {
    if (!job) return
    try { await cancelOptimizationJob(job.id); setGeneration({ job: { ...job, status: 'CANCELLED' }, fingerprint: draftFingerprint }) } catch { setError('취소 요청을 처리하지 못했습니다.') }
  }

  return <section className="optimizer-panel" aria-labelledby="optimizer-title">
    <div className="section-heading"><div><h2 id="optimizer-title">조건에 맞는 시간표</h2><p>선택 유지 설정과 꼭 포함할 과목을 반영합니다.</p></div></div>
    {!job && <><button type="button" className="primary-button full-button" onClick={generate} disabled={busy || !canGenerate}><SlidersIcon />{busy ? '요청 중…' : '시간표 3개 만들기'}</button>{!canGenerate && <p className="helper-copy">최소 {draft.preferences.minCredits}학점을 채울 만큼 꼭 포함·선호·예비 과목을 먼저 추가해 주세요.</p>}</>}
    {job && !DONE.has(job.status) && <div className="job-status" role="status"><span className="spinner" aria-hidden="true"/><div><strong>{job.status === 'QUEUED' ? '대기 중' : '후보 생성 중'}</strong><p>가짜 진행률 없이 실제 작업 상태만 표시합니다.</p></div><button type="button" onClick={cancel}>취소</button></div>}
    {error && <div className="inline-error" role="alert">{error}</div>}
    {staleNotice && <p className="stale-candidate-notice" role="status">{staleNotice}</p>}
    {job?.status === 'INFEASIBLE' && <div className="infeasible" role="alert"><strong>모든 조건을 동시에 만족하는 시간표가 없습니다.</strong><ul>{job.relaxationSuggestions.map((suggestion) => <li key={suggestion}>{suggestion}</li>)}</ul><button type="button" className="secondary-button" onClick={generate}>조건을 바꾼 뒤 다시 생성</button></div>}
    {job?.status === 'TIME_LIMIT' && !job.candidates.length && <div className="inline-error">제한 시간 안에 후보를 찾지 못했습니다. 후보 과목 수를 줄이거나 조건을 완화해 주세요.</div>}
    {!!job?.candidates.length && <div className="candidate-list" aria-label="자동 생성 후보">
      {job.candidates.slice(0, 3).map((candidate, index) => {
        const diff = diffCandidate(candidate.sectionIds, draft.items, sectionById)
        return <article className="candidate" key={candidate.id}>
        <div className="candidate-heading"><div><span>후보 {index + 1}</span><h3>{candidate.metrics.campusDays}일 등교 · {candidate.metrics.credits}학점</h3></div><strong>{candidate.metrics.totalGapMinutes}분 공강</strong></div>
        <dl><div><dt>첫 수업</dt><dd>{candidate.metrics.earliest ?? '없음'}</dd></div><div><dt>마지막 수업</dt><dd>{candidate.metrics.latest ?? '없음'}</dd></div></dl>
        <p className="candidate-change-summary">교체 {diff.swaps.length} · 추가 {diff.added.length} · 제외 {diff.removed.length}</p>
        <ul className="reason-list">{candidate.reasons.slice(0, 3).map((reason) => <li key={reason}><CheckIcon />{reason}</li>)}</ul>
        {!!candidate.unmetPreferences.length && <p className="unmet">미반영: {candidate.unmetPreferences.join(', ')}</p>}
        <button type="button" className={index === 0 ? 'primary-button' : 'secondary-button'} onClick={() => onPreview(candidate, generation!.fingerprint)}>후보 {index + 1} 미리보기</button>
      </article>})}
    </div>}
    {job && DONE.has(job.status) && <button type="button" className="text-button" onClick={generate}>새 조건으로 다시 만들기</button>}
  </section>
}
