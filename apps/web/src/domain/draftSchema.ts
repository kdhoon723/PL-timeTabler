import { DAYS, type DraftSnapshot, type PlanItem, type Preferences } from '../types'

export const DEFAULT_PREFERENCES: Readonly<Preferences> = {
  targetCredits: 18,
  minCredits: 15,
  maxCredits: 21,
  preferredFreeDays: [],
  avoidBefore: null,
  avoidAfter: null,
  minLunchMinutes: 60,
  maxDailyMinutes: 360,
  compactness: 70,
  minimizeChanges: true,
}

const ROLES = new Set<PlanItem['role']>(['must', 'want', 'backup', 'exclude'])
const DAY_SET = new Set<string>(DAYS)
const TIME_PATTERN = /^(?:[01]\d|2[0-3]):[0-5]\d$/

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value)
}

function normalizedNumber(
  source: Record<string, unknown>,
  key: keyof Preferences,
  fallback: number,
  minimum: number,
  maximum: number,
): number | null {
  const value = source[key]
  if (value === undefined) return fallback
  return typeof value === 'number' && Number.isFinite(value) && value >= minimum && value <= maximum ? value : null
}

function normalizedTime(source: Record<string, unknown>, key: 'avoidBefore' | 'avoidAfter'): string | null | undefined {
  const value = source[key]
  if (value === undefined || value === null) return null
  return typeof value === 'string' && TIME_PATTERN.test(value) ? value : undefined
}

export function normalizePreferences(value: unknown): Preferences | null {
  if (!isRecord(value)) return null
  const minCredits = normalizedNumber(value, 'minCredits', DEFAULT_PREFERENCES.minCredits, 0, 30)
  const maxCredits = normalizedNumber(value, 'maxCredits', DEFAULT_PREFERENCES.maxCredits, 0, 30)
  const minLunchMinutes = normalizedNumber(value, 'minLunchMinutes', DEFAULT_PREFERENCES.minLunchMinutes, 0, 150)
  const maxDailyMinutes = normalizedNumber(value, 'maxDailyMinutes', DEFAULT_PREFERENCES.maxDailyMinutes, 0, 24 * 60)
  const compactness = normalizedNumber(value, 'compactness', DEFAULT_PREFERENCES.compactness, 0, 100)
  const avoidBefore = normalizedTime(value, 'avoidBefore')
  const avoidAfter = normalizedTime(value, 'avoidAfter')
  const rawTargetCredits = normalizedNumber(value, 'targetCredits', DEFAULT_PREFERENCES.targetCredits, 0, 30)
  if ([rawTargetCredits, minCredits, maxCredits, minLunchMinutes, maxDailyMinutes, compactness].some((item) => item === null)) return null
  if (![rawTargetCredits, minCredits, maxCredits].every((item) => Number.isInteger(item))) return null
  if (avoidBefore === undefined || avoidAfter === undefined) return null

  const daysValue = value.preferredFreeDays
  const preferredFreeDays = daysValue === undefined
    ? [...DEFAULT_PREFERENCES.preferredFreeDays]
    : Array.isArray(daysValue) && daysValue.every((day) => typeof day === 'string' && DAY_SET.has(day))
      ? [...new Set(daysValue)] as Preferences['preferredFreeDays']
      : null
  const minimizeChanges = value.minimizeChanges === undefined ? DEFAULT_PREFERENCES.minimizeChanges : value.minimizeChanges
  if (!preferredFreeDays || typeof minimizeChanges !== 'boolean') return null
  if (minCredits! > maxCredits!) return null
  const targetCredits = Math.min(maxCredits!, Math.max(minCredits!, rawTargetCredits!))

  return {
    targetCredits,
    minCredits: minCredits!,
    maxCredits: maxCredits!,
    preferredFreeDays,
    avoidBefore,
    avoidAfter,
    minLunchMinutes: minLunchMinutes!,
    maxDailyMinutes: maxDailyMinutes!,
    compactness: compactness!,
    minimizeChanges,
  }
}

export function normalizeDraftSnapshot(value: unknown): DraftSnapshot | null {
  if (!isRecord(value) || value.schemaVersion !== 1 || typeof value.semester !== 'string' || !value.semester.trim()) return null
  if (!Array.isArray(value.items) || !value.items.every((item) => isRecord(item)
    && typeof item.sectionId === 'string' && !!item.sectionId
    && typeof item.role === 'string' && ROLES.has(item.role as PlanItem['role'])
    && typeof item.locked === 'boolean')) return null
  if (!(value.dataVersion === null || typeof value.dataVersion === 'string')) return null
  if (typeof value.updatedAt !== 'string' || Number.isNaN(Date.parse(value.updatedAt))) return null
  const preferences = normalizePreferences(value.preferences)
  if (!preferences) return null
  return {
    schemaVersion: 1,
    semester: value.semester,
    dataVersion: value.dataVersion,
    items: value.items.map((item) => ({
      sectionId: item.sectionId as string,
      role: item.role as PlanItem['role'],
      locked: (item.role === 'must' || item.role === 'want') && item.locked as boolean,
    })),
    preferences,
    updatedAt: value.updatedAt,
  }
}
