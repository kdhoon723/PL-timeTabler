import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createOptimizationJob, getOptimizationJob } from '../api/client'
import { emptyDraft } from '../state/draft'
import type { OptimizationJob, Section } from '../types'
import { OptimizerPanel } from './OptimizerPanel'

vi.mock('../api/client', () => ({
  createOptimizationJob: vi.fn(),
  getOptimizationJob: vi.fn(),
  cancelOptimizationJob: vi.fn(),
}))

const queued: OptimizationJob = { id: 'job-1', status: 'QUEUED', candidates: [], relaxationSuggestions: [] }
const cancelled: OptimizationJob = { ...queued, status: 'CANCELLED' }
const section: Section = { id: 'A-1', courseCode: 'A', sectionCode: '1', name: 'A', professor: null, category: '전공', credits: 3, rawTime: null, sessions: [] }

describe('optimizer polling recovery', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => { vi.useRealTimers(); vi.clearAllMocks() })

  it('backs off and resumes after a transient status request failure', async () => {
    vi.mocked(createOptimizationJob).mockResolvedValue(queued)
    vi.mocked(getOptimizationJob).mockRejectedValueOnce(new Error('temporary 502')).mockResolvedValueOnce(cancelled)
    const draft = { ...emptyDraft(), dataVersion: 'version', items: [{ sectionId: 'A-1', role: 'want' as const, locked: false }], preferences: { ...emptyDraft().preferences, minCredits: 3 } }
    render(<OptimizerPanel draft={draft} sections={[section]} onApply={() => undefined} />)

    await act(async () => { fireEvent.click(screen.getByRole('button', { name: '시간표 3개 만들기' })) })
    expect(screen.getByText('대기 중')).toBeInTheDocument()
    await act(async () => { await vi.advanceTimersByTimeAsync(900) })
    expect(screen.getByText('자동 생성 상태 연결이 잠시 끊겼습니다. 자동으로 다시 확인합니다.')).toBeInTheDocument()
    await act(async () => { await vi.advanceTimersByTimeAsync(1_800) })

    expect(getOptimizationJob).toHaveBeenCalledTimes(2)
    expect(screen.getByRole('button', { name: '새 조건으로 다시 만들기' })).toBeInTheDocument()
  })
})
