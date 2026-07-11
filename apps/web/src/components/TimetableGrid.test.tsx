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
  it('assigns vivid course colors by timetable insertion order', () => {
    const first = section('Z-1', '첫 번째 과목')
    const second = section('A-1', '두 번째 과목')
    const third = section('M-1', '세 번째 과목')

    render(<TimetableGrid sections={[first, second, third]} conflicts={[]} lockedIds={new Set()} onSelect={() => undefined} />)

    expect(screen.getByRole('button', { name: /첫 번째 과목/ })).toHaveClass('course-0')
    expect(screen.getByRole('button', { name: /두 번째 과목/ })).toHaveClass('course-1')
    expect(screen.getByRole('button', { name: /세 번째 과목/ })).toHaveClass('course-2')
  })

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
    expect(screen.getByRole('heading', { name: '내 시간표' }).parentElement).toHaveTextContent('1개 분반')
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
    const alternative = { ...section('A-2', '알고리즘'), sectionCode: '02' }
    const common = { sections: [current], conflicts: [], onSelect: () => undefined, dragAlternativesById: new Map([[current.id, [alternative]]]) }
    const { rerender } = render(<TimetableGrid {...common} lockedIds={new Set([current.id])} dragEnabled onReplace={() => undefined} />)
    expect(screen.getByRole('button', { name: /알고리즘 월/ })).toHaveAttribute('draggable', 'false')

    rerender(<TimetableGrid {...common} lockedIds={new Set()} dragEnabled={false} onReplace={() => undefined} />)
    expect(screen.getByRole('button', { name: /알고리즘 월/ })).toHaveAttribute('draggable', 'false')

    rerender(<TimetableGrid {...common} lockedIds={new Set()} dragEnabled previewStatusById={new Map([['A-1', 'kept']])} onReplace={() => undefined} />)
    expect(screen.getByLabelText(/미리보기에서 유지/)).toHaveAttribute('draggable', 'false')

    rerender(<TimetableGrid {...common} lockedIds={new Set()} dragEnabled dragAlternativesById={new Map([[current.id, [{ ...alternative, sessions: [] }]]])} onReplace={() => undefined} />)
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

  it('groups coincident official slots and requires an accessible explicit section choice', () => {
    const current = section('A-1', '알고리즘')
    const alternative2 = { ...section('A-2', '알고리즘'), sectionCode: '02' }
    const alternative3 = { ...section('A-3', '알고리즘'), sectionCode: '03' }
    const onReplace = vi.fn()
    const dataTransfer = { setData: vi.fn(), effectAllowed: '', dropEffect: '' }
    const { container } = render(<TimetableGrid sections={[current]} conflicts={[]} lockedIds={new Set()} onSelect={() => undefined} dragEnabled dragAlternativesById={new Map([[current.id, [alternative2, alternative3]]])} onReplace={onReplace} />)
    const source = screen.getByRole('button', { name: /알고리즘 월/ })
    source.focus()

    fireEvent.dragStart(source, { dataTransfer })
    const slots = container.querySelectorAll<HTMLElement>('[data-drop-slot-key="월-10:30-12:00"]')
    expect(slots).toHaveLength(1)
    expect(slots[0]).toHaveTextContent('2개 분반 중 선택')
    fireEvent.drop(slots[0]!, { dataTransfer })

    const chooser = screen.getByRole('dialog', { name: '같은 시간 분반 선택' })
    const choice2 = screen.getByRole('button', { name: /02분반 선택/ })
    const choice3 = screen.getByRole('button', { name: /03분반 선택/ })
    expect(chooser).toContainElement(choice2)
    expect(chooser).toContainElement(choice3)
    expect(choice2).toHaveFocus()
    fireEvent.keyDown(chooser, { key: 'Escape' })
    expect(screen.queryByRole('dialog', { name: '같은 시간 분반 선택' })).not.toBeInTheDocument()
    expect(source).toHaveFocus()

    fireEvent.dragStart(source, { dataTransfer })
    fireEvent.drop(container.querySelector<HTMLElement>('[data-drop-slot-key="월-10:30-12:00"]')!, { dataTransfer })
    fireEvent.click(screen.getByRole('button', { name: /03분반 선택/ }))
    expect(onReplace).toHaveBeenCalledWith(current, alternative3)
    expect(screen.getByRole('heading', { name: '내 시간표' })).toHaveFocus()
  })
})
