import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { Section } from '../types'
import { CourseSearchSheet } from './CourseSearchSheet'

const catalog: Section[] = [
  { id: '922601-01', courseCode: '922601', sectionCode: '01', name: 'AI시대의컴퓨팅사고', professor: '김선경', category: '교양필수', credits: 2, rawTime: null, sessions: [{ day: '화', start: '11:30', end: '13:30', room: '인101', building: '인문학관' }] },
  { id: '922601-02', courseCode: '922601', sectionCode: '02', name: 'AI시대의컴퓨팅사고', professor: '박효진', category: '교양필수', credits: 2, rawTime: null, sessions: [{ day: '금', start: '09:30', end: '11:30', room: null, building: null }] },
]

describe('course search sheet', () => {
  it('groups sections and adds a section in two actions', async () => {
    const onAdd = vi.fn()
    render(<CourseSearchSheet open sections={catalog} items={[]} onClose={() => undefined} onAdd={onAdd} />)
    const input = screen.getByRole('textbox', { name: '과목명, 교수, 과목코드 검색' })
    await userEvent.type(input, '김선경')
    const results = screen.getByRole('button', { name: /01분반/ })
    await userEvent.click(results)
    expect(onAdd).toHaveBeenCalledWith(catalog[0])
    expect(within(screen.getByRole('dialog')).getByText('1개 분반')).toBeInTheDocument()
  })
})
