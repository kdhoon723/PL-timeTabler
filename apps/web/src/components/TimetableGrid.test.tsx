import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { CandidatePreviewState } from '../domain/candidateDiff'
import type { Section } from '../types'
import { TimetableGrid } from './TimetableGrid'

const section = (id: string, name: string): Section => ({
  id,
  courseCode: id.split('-')[0]!,
  sectionCode: id.split('-')[1]!,
  name,
  professor: null,
  category: '전공',
  credits: 3,
  rawTime: null,
  sessions: [{ day: '월', start: id === 'A-1' ? '09:00' : '10:30', end: id === 'A-1' ? '10:30' : '12:00', room: null, building: null }],
})

afterEach(cleanup)

describe('timetable candidate preview', () => {
  it('announces and styles preview states without opening the saved-draft detail sheet', () => {
    const removed = section('A-1', '알고리즘')
    const added = section('B-1', '운영체제')
    const onSelect = vi.fn()

    render(<TimetableGrid
      sections={[removed, added]}
      conflicts={[]}
      lockedIds={new Set()}
      onSelect={onSelect}
      previewStatusById={new Map<string, CandidatePreviewState>([['A-1', 'removed'], ['B-1', 'added']])}
    />)

    expect(screen.getByLabelText(/알고리즘.*미리보기에서 제외/)).toHaveClass('preview-removed')
    expect(screen.getByLabelText(/운영체제.*미리보기에서 추가/)).toHaveClass('preview-added')
    expect(onSelect).not.toHaveBeenCalled()
  })
})

describe('guided desktop section drag', () => {
  it('reveals only canonical alternative slots and replaces on drop', () => {
    const current = section('A-1', '알고리즘')
    const alternative = { ...section('A-2', '알고리즘'), sectionCode: '02' }
    const onReplace = vi.fn()
    const dataTransfer = { setData: vi.fn(), effectAllowed: '', dropEffect: '' }

    const { container } = render(<TimetableGrid
      sections={[current]}
      conflicts={[]}
      lockedIds={new Set()}
      onSelect={() => undefined}
      dragEnabled
      dragAlternativesById={new Map([[current.id, [alternative]]])}
      onReplace={onReplace}
    />)

    const source = screen.getByRole('button', { name: /알고리즘 월/ })
    expect(source).toHaveAttribute('draggable', 'true')
    fireEvent.dragStart(source, { dataTransfer })

    const slot = container.querySelector<HTMLElement>('[data-drop-section-id="A-2"]')
    expect(slot).not.toBeNull()
    expect(slot).toHaveTextContent('02분반으로 교체')
    fireEvent.dragOver(slot!, { dataTransfer })
    fireEvent.drop(slot!, { dataTransfer })

    expect(dataTransfer.setData).toHaveBeenCalledWith('text/plain', current.id)
    expect(onReplace).toHaveBeenCalledWith(current, alternative)
    expect(screen.getByRole('status')).toHaveTextContent('알고리즘 02분반으로 교체했습니다')
  })

  it('never makes locked, mobile-width, or candidate-preview blocks draggable', () => {
    const current = section('A-1', '알고리즘')
    const common = { sections: [current], conflicts: [], onSelect: () => undefined, dragAlternativesById: new Map([[current.id, []]]) }
    const { rerender } = render(<TimetableGrid {...common} lockedIds={new Set([current.id])} dragEnabled onReplace={() => undefined} />)
    expect(screen.getByRole('button', { name: /알고리즘 월/ })).toHaveAttribute('draggable', 'false')

    rerender(<TimetableGrid {...common} lockedIds={new Set()} dragEnabled={false} onReplace={() => undefined} />)
    expect(screen.getByRole('button', { name: /알고리즘 월/ })).toHaveAttribute('draggable', 'false')

    rerender(<TimetableGrid {...common} lockedIds={new Set()} dragEnabled previewStatusById={new Map([['A-1', 'kept']])} onReplace={() => undefined} />)
    expect(screen.getByLabelText(/미리보기에서 유지/)).toHaveAttribute('draggable', 'false')

    rerender(<TimetableGrid {...common} lockedIds={new Set()} dragEnabled dragAlternativesById={new Map([[current.id, [{ ...section('A-2', '알고리즘'), sessions: [] }]]])} onReplace={() => undefined} />)
    expect(screen.getByRole('button', { name: /알고리즘 월/ })).toHaveAttribute('draggable', 'false')
  })

  it('includes every official alternative session in drag bounds and keeps one section hover target', () => {
    const current = section('A-1', '알고리즘')
    const alternative: Section = {
      ...section('A-2', '알고리즘'),
      sectionCode: '02',
      sessions: [
        { day: '화', start: '07:00', end: '08:00', room: '101', building: null },
        { day: '토', start: '20:00', end: '21:30', room: '202', building: null },
      ],
    }
    const dataTransfer = { setData: vi.fn(), effectAllowed: '', dropEffect: '' }
    const { container } = render(<TimetableGrid sections={[current]} conflicts={[]} lockedIds={new Set()} onSelect={() => undefined} dragEnabled dragAlternativesById={new Map([[current.id, [alternative]]])} onReplace={() => undefined} />)

    const source = screen.getByRole('button', { name: /알고리즘 월/ })
    expect(source).toHaveAccessibleDescription(/표시되는 공식 분반 시간에 놓으세요/)
    fireEvent.dragStart(source, { dataTransfer })

    expect(screen.getByText('토')).toBeInTheDocument()
    expect(container.querySelector('.time-axis')).toHaveTextContent('07:00')
    expect(container.querySelector('.time-axis')).toHaveTextContent('21:00')
    const slots = [...container.querySelectorAll<HTMLElement>('[data-drop-section-id="A-2"]')]
    expect(slots).toHaveLength(2)
    fireEvent.dragEnter(slots[0]!)
    expect(slots.every((slot) => slot.classList.contains('active'))).toBe(true)
    fireEvent.dragLeave(slots[0]!, { relatedTarget: slots[1] })
    expect(slots.every((slot) => slot.classList.contains('active'))).toBe(true)
  })

  it('suppresses the click emitted after dragging instead of opening details', () => {
    const current = section('A-1', '알고리즘')
    const alternative = { ...section('A-2', '알고리즘'), sectionCode: '02' }
    const onSelect = vi.fn()
    const dataTransfer = { setData: vi.fn(), effectAllowed: '', dropEffect: '' }
    const { container } = render(<TimetableGrid sections={[current]} conflicts={[]} lockedIds={new Set()} onSelect={onSelect} dragEnabled dragAlternativesById={new Map([[current.id, [alternative]]])} onReplace={() => undefined} />)

    const source = screen.getByRole('button', { name: /알고리즘 월/ })
    fireEvent.dragStart(source, { dataTransfer })
    expect(screen.getByRole('status')).toHaveTextContent('표시된 분반 시간에 놓으세요')
    fireEvent.dragEnd(source, { dataTransfer })
    fireEvent.click(source)

    expect(onSelect).not.toHaveBeenCalled()
    expect(container.querySelector('[data-drop-section-id]')).not.toBeInTheDocument()
  })
})
