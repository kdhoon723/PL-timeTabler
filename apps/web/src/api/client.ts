import { timeToMinutes } from '../domain/time'
import type {
  AuthSession,
  Catalog,
  CommonRules,
  CompletedCourse,
  CompletedCourseStatus,
  CourseReview,
  CourseStats,
  CreditSummary,
  DepartmentSources,
  DraftSnapshot,
  HistoricalCourseDetail,
  HistoricalCourseOffering,
  HistoricalSemester,
  MajorRequiredCourses,
  OptimizationJob,
  PrivacyConsent,
  RatingSummary,
  SavedTimetable,
  SavedTimetableDetail,
  Section,
  UserInfo,
} from '../types'

const CATALOG_CACHE_KEY = 'pl-timetabler:catalog:v1'

export class ApiError extends Error {
  constructor(public status: number, message: string, public retryAfter: string | null = null) {
    super(message)
  }
}

async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(url, { credentials: 'same-origin', ...init, headers: { 'Content-Type': 'application/json', ...init?.headers } })
  } catch {
    throw new ApiError(0, '네트워크에 연결할 수 없습니다. 연결 상태를 확인한 뒤 다시 시도해 주세요.')
  }
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`
    try {
      const body = await response.json() as { detail?: unknown }
      if (typeof body.detail === 'string') detail = body.detail
      else if (body.detail && typeof body.detail === 'object') detail = JSON.stringify(body.detail)
    } catch { /* keep the HTTP status */ }
    if (response.status === 401 && !url.startsWith('/api/v1/auth/')) window.dispatchEvent(new CustomEvent('timetabler:session-expired'))
    if (response.status === 403) detail = '이 요청을 처리할 권한이 없습니다.'
    if (response.status === 404) detail = '요청한 정보를 찾을 수 없습니다.'
    if (response.status === 429) detail = '요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.'
    if (response.status >= 500) detail = '서버에서 요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.'
    throw new ApiError(response.status, detail, response.headers.get('Retry-After'))
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

function isCatalog(value: unknown): value is Catalog {
  return !!value && typeof value === 'object' && 'sections' in value && Array.isArray(value.sections)
}

interface ApiCatalogPage {
  semester: string
  preparedAt: string
  datasetVersion: string
  sections: Array<{
    id: string
    courseCode: string
    sectionCode: string
    name: string
    professor: string | null
    category: string
    credits: number
    rawLectureTime: string
    sessions: Array<{
      day: Section['sessions'][number]['day']
      startMinute: number
      endMinute: number
      roomName: string | null
      buildingName: string | null
    }>
  }>
}

function minutesToTime(value: number): string {
  return `${String(Math.floor(value / 60)).padStart(2, '0')}:${String(value % 60).padStart(2, '0')}`
}

function normalizeApiCatalog(page: ApiCatalogPage): Catalog {
  return {
    schemaVersion: 1,
    semester: page.semester,
    dataVersion: page.datasetVersion,
    updatedAt: page.preparedAt,
    source: { label: '대진대학교 공개 개설과목', url: 'https://www.daejin.ac.kr/' },
    sections: page.sections.map((section) => ({
      id: section.id,
      courseCode: section.courseCode,
      sectionCode: section.sectionCode,
      name: section.name,
      professor: section.professor,
      category: section.category,
      credits: section.credits,
      rawTime: section.rawLectureTime || null,
      sessions: section.sessions.map((session) => ({
        day: session.day,
        start: minutesToTime(session.startMinute),
        end: minutesToTime(session.endMinute),
        room: session.roomName,
        building: session.buildingName,
      })),
    })),
  }
}

export async function loadCatalog(semester = '2026-1'): Promise<{ catalog: Catalog; offline: boolean }> {
  try {
    const page = await jsonFetch<ApiCatalogPage>(`/api/v1/catalog/${encodeURIComponent(semester)}?limit=2000`)
    const catalog = normalizeApiCatalog(page)
    try { localStorage.setItem(CATALOG_CACHE_KEY, JSON.stringify(catalog)) } catch { /* cache is best effort */ }
    return { catalog, offline: false }
  } catch { /* fall through to packaged and browser caches */ }
  for (const url of [`/data/catalog-${semester}.json`]) {
    try {
      const catalog = await jsonFetch<Catalog>(url)
      if (!isCatalog(catalog)) throw new Error('카탈로그 형식이 올바르지 않습니다.')
      try { localStorage.setItem(CATALOG_CACHE_KEY, JSON.stringify(catalog)) } catch { /* cache is best effort */ }
      return { catalog, offline: url.startsWith('/data/') }
    } catch { /* use next source */ }
  }
  try {
    const cached: unknown = JSON.parse(localStorage.getItem(CATALOG_CACHE_KEY) ?? 'null')
    if (isCatalog(cached)) return { catalog: cached, offline: true }
  } catch { /* no usable cache */ }
  throw new Error('강의 데이터를 불러오지 못했습니다. 네트워크를 확인한 뒤 다시 시도해 주세요.')
}

export async function loadCommonRules(): Promise<CommonRules> {
  try { return await jsonFetch<CommonRules>('/api/v1/requirements/common') }
  catch { return jsonFetch<CommonRules>('/data/common-graduation-rules.json') }
}

export function loadDepartmentSources(): Promise<DepartmentSources> {
  return jsonFetch<DepartmentSources>('/data/department-sources-2026.json')
}

export function loadMajorRequiredCourses(): Promise<MajorRequiredCourses> {
  return jsonFetch<MajorRequiredCourses>('/data/major-required-courses-2026.json')
}

export function loadAuthSession(): Promise<AuthSession> {
  return jsonFetch<AuthSession>('/api/v1/auth/session')
}

export function startEmailOtp(studentNumber: string): Promise<{ message: string }> {
  return jsonFetch('/api/v1/auth/otp/start', { method: 'POST', body: JSON.stringify({ studentNumber }) })
}

export function verifyEmailOtp(studentNumber: string, code: string): Promise<AuthSession> {
  return jsonFetch('/api/v1/auth/otp/verify', { method: 'POST', body: JSON.stringify({ studentNumber, code }) })
}

export function logoutAuthSession(): Promise<void> {
  return jsonFetch('/api/v1/auth/logout', { method: 'POST' })
}

export function loadCurrentUser(): Promise<UserInfo> {
  return jsonFetch('/api/v1/users/me')
}

export function updateCurrentUser(values: Partial<Pick<UserInfo, 'name' | 'grade' | 'department' | 'admissionYear' | 'entryType' | 'studentType' | 'sectionGroup' | 'majorPath'>>): Promise<UserInfo> {
  return jsonFetch('/api/v1/users/me', { method: 'PATCH', body: JSON.stringify(values) })
}

export function createPrivacyConsent(consentVersion = '2026-07'): Promise<PrivacyConsent> {
  return jsonFetch('/api/v1/users/me/consents', { method: 'POST', body: JSON.stringify({ consentVersion, agreed: true }) })
}

export function loadPrivacyConsents(): Promise<PrivacyConsent[]> {
  return jsonFetch('/api/v1/users/me/consents')
}

export function deleteCurrentUser(confirmation: string): Promise<{ message: string; deletedAt: string }> {
  return jsonFetch('/api/v1/users/me', { method: 'DELETE', body: JSON.stringify({ confirmation }) })
}

export function loadCourseStats(): Promise<CourseStats[]> {
  return jsonFetch<{ courses: CourseStats[] }>('/api/v1/courses?sort=NAME&order=ASC&size=2000').then((value) => value.courses)
}

export function createSavedTimetable(name: string, draft: DraftSnapshot): Promise<SavedTimetableDetail> {
  return jsonFetch('/api/v1/timetables', { method: 'POST', body: JSON.stringify({
    name,
    semester: draft.semester,
    dataVersion: draft.dataVersion,
    items: draft.items,
    preferences: draft.preferences,
  }) })
}

export function loadSavedTimetables(filters: { semester?: string; favorite?: boolean } = {}): Promise<SavedTimetable[]> {
  const query = new URLSearchParams()
  if (filters.semester) query.set('semester', filters.semester)
  if (filters.favorite !== undefined) query.set('favorite', String(filters.favorite))
  const suffix = query.size ? `?${query}` : ''
  return jsonFetch<{ timetables: SavedTimetable[] }>(`/api/v1/timetables${suffix}`).then((value) => value.timetables)
}

export function updateSavedTimetable(id: string, values: { name?: string; preferences?: DraftSnapshot['preferences'] }): Promise<SavedTimetable> {
  return jsonFetch(`/api/v1/timetables/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(values) })
}

export function updateSavedTimetableSections(id: string, draft: DraftSnapshot): Promise<SavedTimetableDetail> {
  return jsonFetch(`/api/v1/timetables/${encodeURIComponent(id)}/sections`, { method: 'PATCH', body: JSON.stringify({ items: draft.items, dataVersion: draft.dataVersion }) })
}

export function deleteSavedTimetable(id: string): Promise<void> {
  return jsonFetch(`/api/v1/timetables/${encodeURIComponent(id)}`, { method: 'DELETE' })
}

export function copySavedTimetable(id: string, name?: string): Promise<SavedTimetableDetail> {
  return jsonFetch(`/api/v1/timetables/${encodeURIComponent(id)}/copy`, { method: 'POST', body: JSON.stringify({ name }) })
}

export function setSavedTimetableFavorite(id: string, favorite: boolean): Promise<SavedTimetable> {
  return jsonFetch(`/api/v1/timetables/${encodeURIComponent(id)}/favorite`, { method: 'PATCH', body: JSON.stringify({ favorite }) })
}

export function createTimetableShare(id: string): Promise<{ shareCode: string; shareUrl: string; expiresAt: string | null }> {
  return jsonFetch(`/api/v1/timetables/${encodeURIComponent(id)}/shares`, { method: 'POST', body: '{}' })
}

export function loadSharedTimetable(code: string): Promise<{ timetable: SavedTimetable; sections: Section[] }> {
  return jsonFetch(`/api/v1/shared-timetables/${encodeURIComponent(code)}`)
}

interface ReviewListResponse {
  reviews: CourseReview[]
  ratingSummary: RatingSummary
  total: number
}

export function loadCourseReviews(courseCode: string, professor?: string): Promise<ReviewListResponse> {
  const query = new URLSearchParams()
  if (professor) query.set('professor', professor)
  return jsonFetch(`/api/v1/courses/${encodeURIComponent(courseCode)}/reviews${query.size ? `?${query}` : ''}`)
}

export function createCourseReview(courseCode: string, values: { professor: string | null; semester: string; rating: number; content: string }): Promise<{ review: CourseReview; ratingSummary: RatingSummary }> {
  return jsonFetch(`/api/v1/courses/${encodeURIComponent(courseCode)}/reviews`, { method: 'POST', body: JSON.stringify(values) })
}

export function loadMyReviews(): Promise<CourseReview[]> {
  return jsonFetch<ReviewListResponse>('/api/v1/users/me/reviews').then((value) => value.reviews)
}

export function updateCourseReview(id: string, values: { rating?: number; content?: string }): Promise<{ review: CourseReview; ratingSummary: RatingSummary }> {
  return jsonFetch(`/api/v1/reviews/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(values) })
}

export function deleteCourseReview(id: string): Promise<void> {
  return jsonFetch(`/api/v1/reviews/${encodeURIComponent(id)}`, { method: 'DELETE' })
}

interface CompletedCourseListResponse {
  completedCourses: CompletedCourse[]
  creditSummary: CreditSummary
}

export function loadCompletedCourses(): Promise<CompletedCourseListResponse> {
  return jsonFetch('/api/v1/users/me/completed-courses')
}

export function createCompletedCourse(values: { courseCode?: string | null; courseName: string; credits: number; category: string; area?: string | null; semester?: string | null; status: CompletedCourseStatus }): Promise<CompletedCourse> {
  return jsonFetch('/api/v1/users/me/completed-courses', { method: 'POST', body: JSON.stringify(values) })
}

export function updateCompletedCourse(id: string, values: Partial<Pick<CompletedCourse, 'courseCode' | 'courseName' | 'credits' | 'category' | 'area' | 'semester' | 'status'>>): Promise<CompletedCourse> {
  return jsonFetch(`/api/v1/users/me/completed-courses/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(values) })
}

export function deleteCompletedCourse(id: string): Promise<void> {
  return jsonFetch(`/api/v1/users/me/completed-courses/${encodeURIComponent(id)}`, { method: 'DELETE' })
}

export function importTimetableCourses(id: string): Promise<{ importedCourses: CompletedCourse[]; skippedCourses: string[] }> {
  return jsonFetch('/api/v1/users/me/completed-courses/import-timetable', { method: 'POST', body: JSON.stringify({ timetableId: id, status: 'IN_PROGRESS' }) })
}

export function loadHistoricalSemesters(): Promise<{ semesters: HistoricalSemester[]; totalCourses: number }> {
  return jsonFetch('/api/v1/history/semesters')
}

export function loadHistoricalCourses(filters: { semester: string; q?: string; department?: string; category?: string; page?: number; size?: number }): Promise<{ courses: HistoricalCourseOffering[]; page: number; size: number; total: number }> {
  const query = new URLSearchParams({ semester: filters.semester })
  if (filters.q) query.set('q', filters.q)
  if (filters.department) query.set('department', filters.department)
  if (filters.category) query.set('category', filters.category)
  if (filters.page) query.set('page', String(filters.page))
  if (filters.size) query.set('size', String(filters.size))
  return jsonFetch(`/api/v1/history/courses?${query}`)
}

export function loadHistoricalCourseDetail(id: string): Promise<HistoricalCourseDetail> {
  return jsonFetch(`/api/v1/history/courses/${encodeURIComponent(id)}`)
}

export function importHistoricalCourses(offeringIds: string[]): Promise<{ importedCourses: CompletedCourse[]; skippedOfferingIds: string[] }> {
  return jsonFetch('/api/v1/users/me/completed-courses/import-history', { method: 'POST', body: JSON.stringify({ offeringIds, status: 'COMPLETED' }) })
}

export async function createOptimizationJob(draft: DraftSnapshot, sections: readonly Section[]): Promise<OptimizationJob> {
  if (!draft.dataVersion) throw new Error('강의 데이터 버전을 확인한 뒤 다시 시도해 주세요.')
  const sectionById = new Map(sections.map((section) => [section.id, section]))
  const courseCodes = (roles: ReadonlySet<string>) => [...new Set(draft.items
    .filter((item) => roles.has(item.role))
    .map((item) => sectionById.get(item.sectionId)?.courseCode)
    .filter((value): value is string => !!value))]
  const selectedSectionIds = draft.items
    .filter((item) => item.role === 'must' || item.role === 'want')
    .map((item) => item.sectionId)
  const activeCourseCodes = new Set(courseCodes(new Set(['must', 'want', 'backup'])))
  const raw = await jsonFetch<unknown>('/api/v1/optimizations', { method: 'POST', body: JSON.stringify({
    semester: draft.semester,
    datasetVersion: draft.dataVersion,
    requiredCourseCodes: courseCodes(new Set(['must'])),
    candidateCourseCodes: courseCodes(new Set(['want', 'backup'])),
    excludedCourseCodes: courseCodes(new Set(['exclude'])).filter((courseCode) => !activeCourseCodes.has(courseCode)),
    selectedSectionIds,
    lockedSectionIds: draft.items.filter((item) => item.locked && (item.role === 'must' || item.role === 'want')).map((item) => item.sectionId),
    professorConstraints: draft.items.flatMap((item) => {
      if (!item.professorLocked || (item.role !== 'must' && item.role !== 'want')) return []
      const section = sectionById.get(item.sectionId)
      return section?.professor ? [{ courseCode: section.courseCode, professor: section.professor }] : []
    }),
    minCredits: draft.preferences.minCredits,
    maxCredits: draft.preferences.maxCredits,
    targetCredits: draft.preferences.targetCredits,
    preferences: {
      preferredDaysOff: draft.preferences.preferredFreeDays,
      excludedDays: draft.preferences.excludedDays,
      avoidBeforeMinute: draft.preferences.avoidBefore ? timeToMinutes(draft.preferences.avoidBefore) : null,
      avoidAfterMinute: draft.preferences.avoidAfter ? timeToMinutes(draft.preferences.avoidAfter) : null,
      hardStartMinute: draft.preferences.hardStart ? timeToMinutes(draft.preferences.hardStart) : null,
      hardEndMinute: draft.preferences.hardEnd ? timeToMinutes(draft.preferences.hardEnd) : null,
      maxGapMinutes: draft.preferences.maxGapMinutes,
      minimizeCampusDays: true,
      minimizeGapMinutes: draft.preferences.compactness > 0,
      gapWeightPercent: draft.preferences.compactness,
      minimizeChanges: draft.preferences.minimizeChanges,
      maxDailyMinutes: draft.preferences.maxDailyMinutes || null,
      minLunchMinutes: draft.preferences.minLunchMinutes,
    },
    candidateCount: 3,
    seed: 42,
    timeLimitSeconds: 8,
  }) })
  return normalizeJob(raw)
}

export async function getOptimizationJob(id: string, signal?: AbortSignal): Promise<OptimizationJob> {
  return normalizeJob(await jsonFetch<unknown>(`/api/v1/optimizations/${encodeURIComponent(id)}`, { signal }))
}

function normalizeJob(raw: unknown): OptimizationJob {
  const value = raw as { id: string; status: string; result?: { candidates?: Array<Record<string, unknown>>; reasons?: string[] }; errorMessage?: string }
  const result = value.result
  const status = value.status === 'OPTIMAL' || value.status === 'FEASIBLE' ? 'SUCCEEDED' : value.status as OptimizationJob['status']
  const candidates = (result?.candidates ?? []).map((candidate) => {
    const metrics = (candidate.metrics ?? {}) as Record<string, unknown>
    const metricNumber = (key: string) => {
      const metric = metrics[key]
      return typeof metric === 'number' ? metric : 0
    }
    const metricTime = (key: string) => {
      const metric = metrics[key]
      return typeof metric === 'number' ? minutesToTime(metric) : null
    }
    return {
      id: `${value.id}-${candidate.rank}`,
      rank: candidate.rank as number,
      status: value.status === 'OPTIMAL' ? 'OPTIMAL' as const : 'FEASIBLE' as const,
      sectionIds: (candidate.sectionIds ?? []) as string[],
      score: ((candidate.scoreComponents as Record<string, number> | undefined)?.weighted ?? 0),
      reasons: (candidate.explanation ?? []) as string[],
      unmetPreferences: (candidate.unmetPreferences ?? []) as string[],
      metrics: {
        credits: metricNumber('totalCredits'),
        campusDays: metricNumber('campusDays'),
        totalGapMinutes: metricNumber('gapMinutes'),
        earliest: metricTime('firstClassMinute'),
        latest: metricTime('lastClassMinute'),
        dailyMinutes: {},
      },
    }
  })
  return { id: value.id, status, candidates, relaxationSuggestions: result?.reasons ?? [], message: value.errorMessage }
}

export async function cancelOptimizationJob(id: string): Promise<void> {
  await jsonFetch(`/api/v1/optimizations/${encodeURIComponent(id)}`, { method: 'DELETE' })
}
