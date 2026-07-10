import { describe, expect, it } from 'vitest'
import type { Section } from '../types'
import { timetableExportLayout } from './exportImage'

describe('PNG timetable export bounds', () => {
  it('includes Saturday and a class ending at 23:00', () => {
    const sections: Section[] = [{
      id: 'late-01', courseCode: 'late', sectionCode: '01', name: '야간수업', professor: null, category: '전공', credits: 3, rawTime: null,
      sessions: [{ day: '토', start: '21:00', end: '23:00', room: null, building: null }],
    }]
    expect(timetableExportLayout(sections)).toMatchObject({ days: ['월', '화', '수', '목', '금', '토'], end: 23 * 60 })
  })
})
