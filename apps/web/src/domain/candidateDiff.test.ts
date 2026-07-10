import { describe, expect, it } from 'vitest'
import type { PlanItem, Section } from '../types'
import { diffCandidate } from './candidateDiff'

const section = (id: string, courseCode: string, sectionCode: string, name = courseCode): Section => ({
  id,
  courseCode,
  sectionCode,
  name,
  professor: null,
  category: '전공',
  credits: 3,
  rawTime: null,
  sessions: [{ day: '월', start: '09:00', end: '10:30', room: null, building: null }],
})

describe('candidate diff', () => {
  it('separates kept, added, removed, and same-course section swaps', () => {
    const sections = [
      section('A-1', 'A', '01', '알고리즘'),
      section('A-2', 'A', '02', '알고리즘'),
      section('B-1', 'B', '01', '운영체제'),
      section('C-1', 'C', '01', '데이터베이스'),
      section('D-1', 'D', '01', '네트워크'),
      section('X-1', 'X', '01', '예비과목'),
    ]
    const current: PlanItem[] = [
      { sectionId: 'A-1', role: 'must', locked: false },
      { sectionId: 'B-1', role: 'want', locked: false },
      { sectionId: 'C-1', role: 'want', locked: false },
      { sectionId: 'X-1', role: 'backup', locked: false },
    ]

    const diff = diffCandidate(['A-2', 'B-1', 'D-1'], current, new Map(sections.map((value) => [value.id, value])))

    expect(diff.kept.map((value) => value.id)).toEqual(['B-1'])
    expect(diff.swaps.map(({ from, to }) => [from.id, to.id])).toEqual([['A-1', 'A-2']])
    expect(diff.removed.map((value) => value.id)).toEqual(['C-1'])
    expect(diff.added.map((value) => value.id)).toEqual(['D-1'])
    expect(Object.fromEntries(diff.previewSections.map(({ section, state }) => [section.id, state]))).toEqual({
      'B-1': 'kept',
      'A-1': 'swapped-out',
      'A-2': 'swapped-in',
      'C-1': 'removed',
      'D-1': 'added',
    })
  })
})
