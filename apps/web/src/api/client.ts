import type { Catalog, CommonRules, DraftSnapshot, OptimizationJob } from '../types'

const CATALOG_CACHE_KEY = 'pl-timetabler:catalog:v1'

async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { ...init, headers: { 'Content-Type': 'application/json', ...init?.headers } })
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`)
  return response.json() as Promise<T>
}

function isCatalog(value: unknown): value is Catalog {
  return !!value && typeof value === 'object' && 'sections' in value && Array.isArray(value.sections)
}

export async function loadCatalog(semester = '2026-1'): Promise<{ catalog: Catalog; offline: boolean }> {
  for (const url of [`/api/v1/catalog?semester=${encodeURIComponent(semester)}`, `/data/catalog-${semester}.json`]) {
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

export async function createOptimizationJob(draft: DraftSnapshot): Promise<OptimizationJob> {
  const raw = await jsonFetch<unknown>('/api/v1/optimizations', { method: 'POST', body: JSON.stringify({
    semester: draft.semester,
    dataVersion: draft.dataVersion,
    items: draft.items,
    preferences: draft.preferences,
    candidateCount: 3,
    seed: 42,
  }) })
  return normalizeJob(raw)
}

export async function getOptimizationJob(id: string): Promise<OptimizationJob> {
  return normalizeJob(await jsonFetch<unknown>(`/api/v1/optimizations/${encodeURIComponent(id)}`))
}

function normalizeJob(raw: unknown): OptimizationJob {
  const value = raw as { id: string; status: string; result?: { candidates?: Array<Record<string, unknown>>; reasons?: string[] }; errorMessage?: string }
  const result = value.result
  const status = value.status === 'OPTIMAL' || value.status === 'FEASIBLE' ? 'SUCCEEDED' : value.status as OptimizationJob['status']
  return { id: value.id, status, candidates: (result?.candidates ?? []).map((c) => { const metrics = (c.metrics ?? {}) as Record<string, number>; return { id: `${value.id}-${c.rank}`, rank: c.rank as number, status: 'OPTIMAL', sectionIds: (c.sectionIds ?? []) as string[], score: ((c.scoreComponents as Record<string, number> | undefined)?.weighted ?? 0), reasons: (c.explanation ?? []) as string[], unmetPreferences: (c.unmetPreferences ?? []) as string[], metrics: { credits: metrics.totalCredits ?? 0, campusDays: metrics.campusDays ?? 0, totalGapMinutes: metrics.gapMinutes ?? 0, earliest: null, latest: null, dailyMinutes: {} } } }), relaxationSuggestions: result?.reasons ?? [], message: value.errorMessage }
}

export async function cancelOptimizationJob(id: string): Promise<void> {
  await jsonFetch(`/api/v1/optimization-jobs/${encodeURIComponent(id)}`, { method: 'DELETE' })
}
