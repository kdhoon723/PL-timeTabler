import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createOptimizationJob, getOptimizationJob } from '../api/client'
import { optimizationDraftFingerprint } from '../domain/optimizationDraft'
import { emptyDraft } from '../state/draft'
import type { Candidate, OptimizationJob, Section } from '../types'
import { OptimizerPanel } from './OptimizerPanel'

vi.mock('../api/client', () => ({
  createOptimizationJob: vi.fn(),
  getOptimizationJob: vi.fn(),
  cancelOptimizationJob: vi.fn(),
}))

const queued: OptimizationJob = { id: 'job-1', status: 'QUEUED', candidates: [], relaxationSuggestions: [] }
const cancelled: OptimizationJob = { ...queued, status: 'CANCELLED' }
const section: Section = { id: 'A-1', courseCode: 'A', sectionCode: '1', name: 'A', professor: null, category: '전공', credits: 3, rawTime: null, sessions: [] }
const alternative: Section = { ...section, id: 'A-2', sectionCode: '2' }
const added: Section = { ...section, id: 'B-1', courseCode: 'B', sectionCode: '1', name: 'B' }
const candidate: Candidate = {
  id: 'candidate-1', rank: 1, status: 'OPTIMAL', sectionIds: ['A-2', 'B-1'], score: 10,
  reasons: ['공강을 줄였습니다.'], unmetPreferences: [],
  metrics: { credits: 6, campusDays: 2, totalGapMinutes: 30, earliest: '09:00', latest: '15:00', dailyMinutes: {} },
}

afterEach(cleanup)

describe('optimizer polling recovery', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => { vi.useRealTimers(); vi.clearAllMocks() })

  it('backs off and resumes after a transient status request failure', async () => {
    vi.mocked(createOptimizationJob).mockResolvedValue(queued)
    vi.mocked(getOptimizationJob).mockRejectedValueOnce(new Error('temporary 502')).mockResolvedValueOnce(cancelled)
    const draft = { ...emptyDraft(), dataVersion: 'version', items: [{ sectionId: 'A-1', role: 'want' as const, locked: false }], preferences: { ...emptyDraft().preferences, minCredits: 3 } }
    render(<OptimizerPanel draft={draft} draftFingerprint={optimizationDraftFingerprint(draft)} sections={[section]} onPreview={() => undefined} />)

    await act(async () => { fireEvent.click(screen.getByRole('button', { name: '시간표 3개 만들기' })) })
    expect(screen.getByText('대기 중')).toBeInTheDocument()
    await act(async () => { await vi.advanceTimersByTimeAsync(900) })
    expect(screen.getByText('자동 생성 상태 연결이 잠시 끊겼습니다. 자동으로 다시 확인합니다.')).toBeInTheDocument()
    await act(async () => { await vi.advanceTimersByTimeAsync(1_800) })

    expect(getOptimizationJob).toHaveBeenCalledTimes(2)
    expect(screen.getByRole('button', { name: '새 조건으로 다시 만들기' })).toBeInTheDocument()
  })
})

describe('optimizer candidate preview', () => {
  afterEach(() => vi.clearAllMocks())

  it('summarizes exact candidate differences and previews instead of applying immediately', async () => {
    vi.mocked(createOptimizationJob).mockResolvedValue({ id: 'job-2', status: 'SUCCEEDED', candidates: [candidate], relaxationSuggestions: [] })
    const onPreview = vi.fn()
    const draft = { ...emptyDraft(), dataVersion: 'version', items: [{ sectionId: 'A-1', role: 'want' as const, locked: false }], preferences: { ...emptyDraft().preferences, minCredits: 3 } }
    render(<OptimizerPanel draft={draft} draftFingerprint={optimizationDraftFingerprint(draft)} sections={[section, alternative, added]} onPreview={onPreview} />)

    await act(async () => { fireEvent.click(screen.getByRole('button', { name: '시간표 3개 만들기' })) })

    expect(screen.getByText('교체 1 · 추가 1 · 제외 0')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '후보 1 미리보기' }))
    expect(onPreview).toHaveBeenCalledWith(candidate, optimizationDraftFingerprint(draft))
    expect(screen.queryByRole('button', { name: '이 후보 적용' })).not.toBeInTheDocument()
  })

  it('discards an in-flight result when any generation condition changes', async () => {
    let resolveJob!: (job: OptimizationJob) => void
    vi.mocked(createOptimizationJob).mockReturnValue(new Promise((resolve) => { resolveJob = resolve }))
    const draft = { ...emptyDraft(), dataVersion: 'version', items: [{ sectionId: 'A-1', role: 'want' as const, locked: false }], preferences: { ...emptyDraft().preferences, minCredits: 3 } }
    const { rerender } = render(<OptimizerPanel draft={draft} draftFingerprint={optimizationDraftFingerprint(draft)} sections={[section, alternative]} onPreview={() => undefined} />)

    fireEvent.click(screen.getByRole('button', { name: '시간표 3개 만들기' }))
    const changedDraft = { ...draft, items: [{ ...draft.items[0]!, locked: true }] }
    rerender(<OptimizerPanel draft={changedDraft} draftFingerprint={optimizationDraftFingerprint(changedDraft)} sections={[section, alternative]} onPreview={() => undefined} />)
    await act(async () => resolveJob({ id: 'job-stale', status: 'SUCCEEDED', candidates: [candidate], relaxationSuggestions: [] }))

    expect(screen.getByRole('status')).toHaveTextContent('조건이 바뀌어 이전 후보를 지웠습니다')
    expect(screen.queryByRole('button', { name: '후보 1 미리보기' })).not.toBeInTheDocument()
  })
})
