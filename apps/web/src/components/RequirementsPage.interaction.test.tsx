import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { CompletedCourse, CreditSummary } from '../types'
import { RequirementsPage } from './RequirementsPage'

const api = vi.hoisted(() => ({
  createCompletedCourse: vi.fn(),
  deleteCompletedCourse: vi.fn(),
  loadCommonRules: vi.fn(),
  loadCompletedCourses: vi.fn(),
  loadDepartmentSources: vi.fn(),
  updateCompletedCourse: vi.fn(),
}))

vi.mock('../api/client', () => api)

let storedCourses: CompletedCourse[] = []

const creditSummary = (): CreditSummary => {
  const completed = storedCourses.filter((item) => item.status === 'COMPLETED')
  return {
    totalCredits: completed.reduce((sum, item) => sum + item.credits, 0),
    majorCredits: completed.filter((item) => item.category.startsWith('전공')).reduce((sum, item) => sum + item.credits, 0),
    liberalCredits: completed.filter((item) => item.category.startsWith('교양')).reduce((sum, item) => sum + item.credits, 0),
    areaCredits: {},
  }
}

describe('graduation requirements completed-course editor', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    storedCourses = []
    api.loadCommonRules.mockResolvedValue({
      schemaVersion: 1,
      asOf: '2026-07-15',
      resultLabel: '예상',
      statuses: [],
      manualReviewReasons: [],
      rules: [{
        id: 'required-data-structures',
        admissionYears: { start: 2020 },
        scope: { studentType: 'DOMESTIC' },
        kind: 'REQUIRED_COURSE_GROUP',
        courses: [{ name: '자료구조', credits: 3 }],
        sourceRefs: [],
      }],
    })
    api.loadDepartmentSources.mockResolvedValue({
      schemaVersion: 1,
      asOf: '2026-07-15',
      source: 'test',
      departments: [{
        college: 'AI융합대학',
        academicUnit: '컴퓨터공학전공',
        unitType: '전공',
        curriculumUrl: null,
        curriculumStatus: '확인',
        graduationUrl: null,
        majorRequiredStatus: '확인',
        prerequisiteStatus: '확인',
        transitionNote: null,
        handbookPage: null,
      }],
    })
    api.loadCompletedCourses.mockImplementation(async () => ({ completedCourses: [...storedCourses], creditSummary: creditSummary() }))
    api.createCompletedCourse.mockImplementation(async (values) => {
      const item: CompletedCourse = {
        id: 'completed-1',
        historicalOfferingId: null,
        courseCode: values.courseCode ?? null,
        sectionCode: null,
        courseName: values.courseName,
        credits: values.credits,
        category: values.category,
        area: values.area ?? null,
        semester: values.semester ?? null,
        status: values.status,
        inputSource: 'MANUAL',
        createdAt: '2026-07-15T00:00:00Z',
        updatedAt: '2026-07-15T00:00:00Z',
      }
      storedCourses = [item]
      return item
    })
    api.updateCompletedCourse.mockImplementation(async (id, values) => {
      storedCourses = storedCourses.map((item) => item.id === id ? { ...item, ...values } : item)
      return storedCourses.find((item) => item.id === id)
    })
    api.deleteCompletedCourse.mockImplementation(async (id) => { storedCourses = storedCourses.filter((item) => item.id !== id) })
  })

  it('adds, edits, deletes, and immediately recalculates a previous course', async () => {
    const user = userEvent.setup()
    render(<RequirementsPage
      catalog={[]}
      profile={{
        schemaVersion: 2,
        department: '컴퓨터공학전공',
        currentGrade: 4,
        academicBasis: { admissionYear: 2022, entryType: 'FRESHMAN', studentType: 'DOMESTIC', sectionGroup: 'UNKNOWN' },
        updatedAt: '2026-07-15T00:00:00Z',
      }}
      authenticated
      onBack={() => undefined}
      onAddCourse={() => undefined}
    />)

    expect(await screen.findByText('저장된 이수과목이 없습니다.')).toBeInTheDocument()
    expect(await screen.findByText(/1과목 중 0과목 입력/)).toBeInTheDocument()

    await user.type(screen.getByRole('textbox', { name: '과목코드' }), '111111')
    await user.type(screen.getByRole('textbox', { name: '과목명' }), '자료구조')
    await user.selectOptions(screen.getByRole('combobox', { name: '수강 학년도' }), '2022')
    await user.selectOptions(screen.getByRole('combobox', { name: /^학기$/ }), '2')
    await user.selectOptions(screen.getByRole('combobox', { name: '이수구분' }), '전공필수')
    await user.click(screen.getByRole('button', { name: '이수과목 추가' }))

    await waitFor(() => expect(api.createCompletedCourse).toHaveBeenCalledWith({
      courseCode: '111111',
      courseName: '자료구조',
      credits: 3,
      category: '전공필수',
      area: null,
      semester: '2022-2',
      status: 'COMPLETED',
    }))
    expect(await screen.findByText(/1과목 중 1과목 입력/)).toBeInTheDocument()
    expect(screen.getByText(/2022-2 · 111111 · 3학점 · 전공필수/)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '수정' }))
    const codeInput = screen.getByRole('textbox', { name: '과목코드' })
    await user.clear(codeInput)
    await user.type(codeInput, '222222')
    await user.click(screen.getByRole('button', { name: '이수과목 수정' }))
    await waitFor(() => expect(api.updateCompletedCourse).toHaveBeenCalledWith('completed-1', expect.objectContaining({ courseCode: '222222' })))
    expect(await screen.findByText(/2022-2 · 222222 · 3학점 · 전공필수/)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '삭제' }))
    await waitFor(() => expect(api.deleteCompletedCourse).toHaveBeenCalledWith('completed-1'))
    expect(await screen.findByText('저장된 이수과목이 없습니다.')).toBeInTheDocument()
    expect(await screen.findByText(/1과목 중 0과목 입력/)).toBeInTheDocument()
  })
})
