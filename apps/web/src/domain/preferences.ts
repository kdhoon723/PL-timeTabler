import type { Preferences } from '../types'

export type PreferencePresetId = 'balanced' | 'compact' | 'free-day' | 'avoid-morning' | 'avoid-late'

type PresetValues = Pick<Preferences, 'avoidBefore' | 'avoidAfter' | 'minLunchMinutes' | 'maxDailyMinutes' | 'compactness' | 'minimizeChanges'>

export interface PreferencePreset {
  id: PreferencePresetId
  label: string
  description: string
  values: PresetValues
}

export const PREFERENCE_PRESETS: readonly PreferencePreset[] = [
  { id: 'balanced', label: '균형 있게', description: '무리 없는 하루와 점심 여유', values: { avoidBefore: null, avoidAfter: null, minLunchMinutes: 60, maxDailyMinutes: 360, compactness: 70, minimizeChanges: true } },
  { id: 'compact', label: '수업 몰아서', description: '수업 사이 빈 시간을 최소화', values: { avoidBefore: null, avoidAfter: null, minLunchMinutes: 30, maxDailyMinutes: 360, compactness: 100, minimizeChanges: false } },
  { id: 'free-day', label: '공강일 우선', description: '선택한 공강 요일을 먼저 확보', values: { avoidBefore: null, avoidAfter: null, minLunchMinutes: 30, maxDailyMinutes: 480, compactness: 100, minimizeChanges: false } },
  { id: 'avoid-morning', label: '오전 수업 피하기', description: '10시 30분 전 수업을 가급적 제외', values: { avoidBefore: '10:30', avoidAfter: null, minLunchMinutes: 60, maxDailyMinutes: 360, compactness: 70, minimizeChanges: true } },
  { id: 'avoid-late', label: '늦은 수업 피하기', description: '17시 이후 수업을 가급적 제외', values: { avoidBefore: null, avoidAfter: '17:00', minLunchMinutes: 60, maxDailyMinutes: 360, compactness: 70, minimizeChanges: true } },
]

const PRESET_KEYS: Array<keyof PresetValues> = ['avoidBefore', 'avoidAfter', 'minLunchMinutes', 'maxDailyMinutes', 'compactness', 'minimizeChanges']

export function applyPreferencePreset(preferences: Preferences, presetId: PreferencePresetId): Preferences {
  const preset = PREFERENCE_PRESETS.find(({ id }) => id === presetId)
  return preset ? { ...preferences, ...preset.values } : preferences
}

export function matchingPreferencePreset(preferences: Preferences): PreferencePresetId | null {
  return PREFERENCE_PRESETS.find(({ values }) => PRESET_KEYS.every((key) => preferences[key] === values[key]))?.id ?? null
}
