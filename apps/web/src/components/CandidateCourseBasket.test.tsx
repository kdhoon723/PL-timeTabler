import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { PlanItem, Section } from '../types'
import { CandidateCourseBasket } from './CandidateCourseBasket'

const sections: Section[] = [
  { id: 'A-01', courseCode: 'A', sectionCode: '01', name: '전공선택 A', professor: null, category: '전공선택', credits: 3, rawTime: null, sessions: [] },
  { id: 'B-01', courseCode: 'B', sectionCode: '01', name: '교양선택 B', professor: null, category: '교양선택', credits: 2, rawTime: null, sessions: [] },
]
const sectionById = new Map(sections.map((section) => [section.id, section]))

afterEach(cleanup)

describe('candidate course basket', () => {
  it('keeps passive choices separate and exposes direct promote, remove, and add actions', async () => {
    const onAdd = vi.fn()
    const onPromote = vi.fn()
    const onRemove = vi.fn()
    const items: PlanItem[] = [
      { sectionId: 'A-01', role: 'backup', locked: false },
      { sectionId: 'B-01', role: 'exclude', locked: false },
    ]
    render(<CandidateCourseBasket items={items} sectionById={sectionById} onAdd={onAdd} onPromote={onPromote} onRemove={onRemove} />)

    expect(screen.getByRole('heading', { name: '자동완성 후보' })).toBeInTheDocument()
    expect(screen.getByText('전공선택 A')).toBeInTheDocument()
    expect(screen.getByText('교양선택 B')).not.toBeVisible()

    await userEvent.click(screen.getByRole('button', { name: '시간표에 넣기' }))
    expect(onPromote).toHaveBeenCalledWith(sections[0])
    await userEvent.click(screen.getByRole('button', { name: '전공선택 A 후보에서 삭제' }))
    expect(onRemove).toHaveBeenCalledWith(sections[0])
    await userEvent.click(screen.getByRole('button', { name: '후보 더 담기' }))
    expect(onAdd).toHaveBeenCalled()

    await userEvent.click(screen.getByText('자동완성에서 제외한 과목 1개'))
    expect(screen.getByText('교양선택 B')).toBeInTheDocument()
  })
})
