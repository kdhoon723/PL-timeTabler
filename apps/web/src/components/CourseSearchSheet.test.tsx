import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Section } from '../types'
import { CourseSearchSheet } from './CourseSearchSheet'

const section = (courseCode: string, sectionCode: string, name: string, day: '월' | '화' | null, start = '09:00'): Section => ({
  id: `${courseCode}-${sectionCode}`,
  courseCode,
  sectionCode,
  name,
  professor: sectionCode === '01' ? '김선경' : '박효진',
  category: '교양필수',
  credits: 2,
  rawTime: null,
  sessions: day ? [{ day, start, end: start === '09:00' ? '10:30' : '13:30', room: null, building: null }] : [],
})

const catalog: Section[] = [
  section('922601', '01', 'AI시대의컴퓨팅사고', '화', '11:30'),
  section('922601', '02', 'AI시대의컴퓨팅사고', null),
  section('100001', '01', '선택과목', '월'),
  section('100001', '02', '선택과목', '화'),
  ...Array.from({ length: 22 }, (_, index) => section(`C${String(index).padStart(5, '0')}`, '01', `과목 ${index + 1}`, '화')),
]

afterEach(cleanup)

describe('course search sheet', () => {
  it('renders at most 20 collapsed course rows and expands only one course at a time', async () => {
    render(<CourseSearchSheet open sections={catalog} items={[]} onClose={() => undefined} onAdd={() => undefined} />)

    const courseRows = screen.getAllByRole('button', { name: /분반 보기/ })
    expect(courseRows).toHaveLength(20)
    expect(courseRows.every((row) => row.getAttribute('aria-expanded') === 'false')).toBe(true)
    expect(screen.queryAllByRole('button', { name: /분반.*추가/ })).toHaveLength(0)

    await userEvent.click(courseRows[0]!)
    expect(courseRows[0]).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getAllByRole('button', { name: /분반.*추가/ }).length).toBeGreaterThan(0)

    await userEvent.click(courseRows[1]!)
    expect(courseRows[0]).toHaveAttribute('aria-expanded', 'false')
    expect(courseRows[1]).toHaveAttribute('aria-expanded', 'true')
  })

  it('announces suggested, conflicting, time-unknown, current, and replacement sections', async () => {
    const onAdd = vi.fn()
    const items = [
      { sectionId: '100001-01', role: 'want' as const, locked: false },
      { sectionId: '922601-01', role: 'want' as const, locked: false },
    ]
    render(<CourseSearchSheet open sections={catalog} items={items} onClose={() => undefined} onAdd={onAdd} />)

    const input = screen.getByRole('textbox', { name: '과목명, 교수, 과목코드 검색' })
    await userEvent.type(input, 'AI시대')
    await userEvent.click(screen.getByRole('button', { name: /AI시대의컴퓨팅사고.*분반 보기/ }))

    const dialog = screen.getByRole('dialog', { name: '과목 추가' })
    expect(within(dialog).getByRole('button', { name: /01분반.*현재 분반/ })).toBeDisabled()
    const replacement = within(dialog).getByRole('button', { name: /02분반.*추천.*시간 미정.*교체/ })
    await userEvent.click(replacement)
    expect(onAdd).toHaveBeenCalledWith(catalog[1])
  })

  it('marks a section that overlaps the current timetable as a conflict', async () => {
    const occupied = section('200001', '01', '기존과목', '화', '11:30')
    render(<CourseSearchSheet open sections={[...catalog, occupied]} items={[{ sectionId: occupied.id, role: 'want', locked: false }]} onClose={() => undefined} onAdd={() => undefined} />)
    await userEvent.type(screen.getByRole('textbox', { name: '과목명, 교수, 과목코드 검색' }), 'AI시대')
    await userEvent.click(screen.getByRole('button', { name: /AI시대의컴퓨팅사고.*분반 보기/ }))
    expect(screen.getByRole('button', { name: /01분반.*충돌.*추가/ })).toBeInTheDocument()
  })
})
