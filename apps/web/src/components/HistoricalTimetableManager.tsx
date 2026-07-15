import { useCallback, useEffect, useMemo, useState } from 'react'
import { importHistoricalCourses, loadHistoricalCourses, loadHistoricalSemesters } from '../api/client'
import type { CompletedCourse, HistoricalCourseOffering, HistoricalSemester } from '../types'

interface Props {
  completedCourses: CompletedCourse[]
  disabled: boolean
  onImported: () => Promise<void>
  onMessage: (message: string) => void
}

const PAGE_SIZE = 30

function contextLabel(context: Record<string, unknown>): string | null {
  const name = typeof context.name === 'string' ? context.name : null
  const area = typeof context.areaName === 'string' ? context.areaName : null
  return [name, area].filter(Boolean).join(' · ') || null
}

export function HistoricalTimetableManager({ completedCourses, disabled, onImported, onMessage }: Props) {
  const [semesters, setSemesters] = useState<HistoricalSemester[]>([])
  const [semester, setSemester] = useState('')
  const [query, setQuery] = useState('')
  const [courses, setCourses] = useState<HistoricalCourseOffering[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const completedCodes = useMemo(() => new Set(completedCourses.map((item) => item.courseCode).filter(Boolean)), [completedCourses])

  const search = useCallback(async (nextPage = 1, nextSemester = semester) => {
    if (!nextSemester) return
    setLoading(true); setError(null)
    try {
      const result = await loadHistoricalCourses({ semester: nextSemester, q: query.trim() || undefined, page: nextPage, size: PAGE_SIZE })
      setCourses(result.courses); setPage(result.page); setTotal(result.total)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : '과거 강의 목록을 불러오지 못했습니다.')
    } finally { setLoading(false) }
  }, [query, semester])

  useEffect(() => {
    loadHistoricalSemesters().then((result) => {
      setSemesters(result.semesters)
      const initial = result.semesters.find((item) => item.courseCount > 0)?.semester ?? result.semesters[0]?.semester ?? ''
      setSemester(initial)
      if (initial) void search(1, initial)
      else setLoading(false)
    }).catch((caught) => {
      setError(caught instanceof Error ? caught.message : '수집된 학기 정보를 불러오지 못했습니다.')
      setLoading(false)
    })
  }, [])

  const toggle = (course: HistoricalCourseOffering) => {
    setSelected((current) => {
      const next = new Set(current)
      if (next.has(course.id)) next.delete(course.id)
      else {
        for (const selectedCourse of courses) {
          if (selectedCourse.courseCode === course.courseCode) next.delete(selectedCourse.id)
        }
        next.add(course.id)
      }
      return next
    })
  }

  const importSelected = async () => {
    if (selected.size === 0) return
    setLoading(true); setError(null)
    try {
      const result = await importHistoricalCourses([...selected])
      setSelected(new Set())
      await onImported()
      onMessage(`${result.importedCourses.length}과목을 과거 이수내역으로 등록했습니다.`)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : '과거 시간표를 등록하지 못했습니다.')
    } finally { setLoading(false) }
  }

  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE))
  return <section id="past-timetable" className="mypage-section historical-manager" aria-labelledby="past-timetable-heading">
    <div className="section-heading"><div><h2 id="past-timetable-heading">과거 시간표 등록</h2><p>2020학년도부터 정규·계절학기 원본 강의정보를 검색해 실제 이수내역으로 연결합니다.</p></div><span>선택 {selected.size}과목</span></div>
    <div className="historical-search">
      <label><span>수강 학기</span><select value={semester} onChange={(event) => { const value = event.target.value; setSemester(value); setSelected(new Set()); void search(1, value) }}>{semesters.map((item) => <option value={item.semester} key={item.semester}>{item.academicYear}학년도 {item.termName} · {item.courseCount.toLocaleString()}분반</option>)}</select></label>
      <label><span>과목 검색</span><input value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') void search(1) }} placeholder="과목명, 학수번호, 교수명" /></label>
      <button type="button" className="secondary-button" disabled={loading || !semester} onClick={() => void search(1)}>검색</button>
    </div>
    {error && <div className="inline-error" role="alert">{error}</div>}
    <div className="historical-result-heading"><p>{loading ? '강의 목록을 불러오는 중입니다…' : `검색 결과 ${total.toLocaleString()}개`}</p><button type="button" className="primary-button" disabled={disabled || loading || selected.size === 0} onClick={() => void importSelected()}>선택 과목 이수 완료로 등록</button></div>
    {!loading && courses.length === 0 && <p className="completed-empty">이 학기에는 조건에 맞는 강의가 없습니다.</p>}
    <div className="historical-course-list">{courses.map((course) => {
      const alreadyCompleted = completedCodes.has(course.courseCode)
      const category = course.categoryContexts.map(contextLabel).filter(Boolean).join(' / ') || course.completionCategory || '이수구분 미상'
      return <article key={course.id} className={selected.has(course.id) ? 'selected' : ''}>
        <label><input type="checkbox" checked={selected.has(course.id)} disabled={alreadyCompleted || disabled} onChange={() => toggle(course)} /><span><strong>{course.koreanName}</strong><small>{course.courseCode}-{course.sectionCode} · {course.credits ?? '?'}학점 · {category}</small><small>{course.professorName || '담당교수 미정'} · {course.rawLectureTime || '시간 미정'} · {course.rawLocation || '장소 미정'}</small></span></label>
        {alreadyCompleted && <span className="status success">등록됨</span>}
      </article>
    })}</div>
    {total > PAGE_SIZE && <div className="history-pagination"><button type="button" disabled={loading || page <= 1} onClick={() => void search(page - 1)}>이전</button><span>{page} / {pageCount}</span><button type="button" disabled={loading || page >= pageCount} onClick={() => void search(page + 1)}>다음</button></div>}
    <p className="source-note">선택한 분반은 학기·학수번호·분반 키로 원본 강의계획서와 연결되며, 수집된 모든 원본 필드는 서버 DB에 그대로 보존됩니다.</p>
  </section>
}
