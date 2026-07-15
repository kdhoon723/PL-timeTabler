import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { HistoricalTimetableManager } from './HistoricalTimetableManager'

const api = vi.hoisted(() => ({
  importHistoricalCourses: vi.fn(),
  loadHistoricalCourses: vi.fn(),
  loadHistoricalSemesters: vi.fn(),
}))

vi.mock('../api/client', () => api)

describe('HistoricalTimetableManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.loadHistoricalSemesters.mockResolvedValue({
      totalCourses: 1,
      semesters: [{ semester: '2020-1', academicYear: 2020, termCode: '1', termName: '1학기', dataStatus: 'FINAL', courseCount: 1, collectedAt: '2026-07-14T00:00:00Z' }],
    })
    api.loadHistoricalCourses.mockResolvedValue({
      page: 1,
      size: 30,
      total: 1,
      courses: [{
        id: 'offering-1', semester: '2020-1', academicYear: 2020, termCode: '1', courseCode: '123456', sectionCode: '01', koreanName: '데이터와 사회', englishName: 'Data and Society', professorName: '홍교수', completionCategory: '교선', credits: 3, lectureHours: 3, practiceHours: 0, rawLectureTime: '월1,2,3', rawLocation: '정보전산원 101', targetGrade: '2', listingStatus: 'LISTED', detailStatus: 'AVAILABLE', categoryContexts: [{ name: '교양선택', areaName: '제1영역:인간과소통' }], departmentContexts: [],
      }],
    })
    api.importHistoricalCourses.mockResolvedValue({
      skippedOfferingIds: [],
      importedCourses: [{ id: 'completed-1', historicalOfferingId: 'offering-1', courseCode: '123456', sectionCode: '01', courseName: '데이터와 사회', credits: 3, category: '교양선택', area: '제1영역:인간과소통', semester: '2020-1', status: 'COMPLETED', inputSource: 'HISTORICAL_TIMETABLE', createdAt: '2026-07-15T00:00:00Z', updatedAt: '2026-07-15T00:00:00Z' }],
    })
  })

  it('selects a collected offering and imports it as completed history', async () => {
    const user = userEvent.setup()
    const onImported = vi.fn().mockResolvedValue(undefined)
    const onMessage = vi.fn()
    render(<HistoricalTimetableManager completedCourses={[]} disabled={false} onImported={onImported} onMessage={onMessage} />)

    expect(await screen.findByText('데이터와 사회')).toBeInTheDocument()
    await user.click(screen.getByRole('checkbox'))
    await user.click(screen.getByRole('button', { name: '선택 과목 이수 완료로 등록' }))

    await waitFor(() => expect(api.importHistoricalCourses).toHaveBeenCalledWith(['offering-1']))
    expect(onImported).toHaveBeenCalledOnce()
    expect(onMessage).toHaveBeenCalledWith('1과목을 과거 이수내역으로 등록했습니다.')
  })
})
