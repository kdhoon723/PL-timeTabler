import { timeToMinutes } from '../domain/time'
import type { AuthSession, Catalog, CommonRules, DepartmentSources, DraftSnapshot, MajorRequiredCourses, OptimizationJob, Section } from '../types'

const CATALOG_CACHE_KEY = 'pl-timetabler:catalog:v1'

async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { credentials: 'same-origin', ...init, headers: { 'Content-Type': 'application/json', ...init?.headers } })
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`
    try {
      const body = await response.json() as { detail?: string }
      if (typeof body.detail === 'string') detail = body.detail
    } catch { /* keep the HTTP status */ }
    throw new Error(detail)
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
      avoidBeforeMinute: draft.preferences.avoidBefore ? timeToMinutes(draft.preferences.avoidBefore) : null,
      avoidAfterMinute: draft.preferences.avoidAfter ? timeToMinutes(draft.preferences.avoidAfter) : null,
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
