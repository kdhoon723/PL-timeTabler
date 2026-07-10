import { describe, expect, it } from 'vitest'
import type { PlanItem, Section } from '../types'
import { findAlternatives, findConflicts } from './conflicts'

const make = (id: string, courseCode: string, day: '월' | '화', start: string, end: string): Section => ({
  id, courseCode, sectionCode: id.at(-1) ?? '1', name: `과목 ${courseCode}`, professor: '교수', category: '전공선택', credits: 3, rawTime: null,
  sessions: [{ day, start, end, room: null, building: null }],
})

describe('conflict graph and alternatives', () => {
  const sections = [make('A-1', 'A', '월', '09:30', '11:30'), make('A-2', 'A', '화', '09:30', '11:30'), make('B-1', 'B', '월', '10:30', '12:30')]
  const byId = new Map(sections.map((section) => [section.id, section]))
  it('returns one undirected edge for two overlapping active courses', () => {
    const items: PlanItem[] = [{ sectionId: 'A-1', role: 'must', locked: false }, { sectionId: 'B-1', role: 'want', locked: false }]
    expect(findConflicts(items, byId)).toHaveLength(1)
  })
  it('does not schedule backup or excluded items', () => {
    const items: PlanItem[] = [{ sectionId: 'A-1', role: 'backup', locked: false }, { sectionId: 'B-1', role: 'exclude', locked: false }]
    expect(findConflicts(items, byId)).toEqual([])
  })
  it('offers only alternatives compatible with the other selected course', () => {
    expect(findAlternatives(sections[0]!, sections, [sections[0]!, sections[2]!]).map((section) => section.id)).toEqual(['A-2'])
  })
})
