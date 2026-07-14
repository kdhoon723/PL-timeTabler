import type { Day, Preferences } from '../types'
import { applyPreferencePreset, matchingPreferencePreset, PREFERENCE_PRESETS } from '../domain/preferences'

interface Props { preferences: Preferences; onChange: (preferences: Preferences) => void }

export function PreferencesPanel({ preferences, onChange }: Props) {
  const activePreset = matchingPreferencePreset(preferences)
  const toggleDay = (day: Day) => onChange({ ...preferences, preferredFreeDays: preferences.preferredFreeDays.includes(day) ? preferences.preferredFreeDays.filter((value) => value !== day) : [...preferences.preferredFreeDays, day], excludedDays: preferences.excludedDays.filter((value) => value !== day) })
  const toggleExcludedDay = (day: Day) => onChange({ ...preferences, excludedDays: preferences.excludedDays.includes(day) ? preferences.excludedDays.filter((value) => value !== day) : [...preferences.excludedDays, day], preferredFreeDays: preferences.preferredFreeDays.filter((value) => value !== day) })
  const wholeCredits = (value: number) => Math.min(30, Math.max(1, Math.round(value || 1)))
  const setTargetCredits = (targetCredits: number) => onChange({
    ...preferences,
    targetCredits: wholeCredits(targetCredits),
    minCredits: Math.min(preferences.minCredits, wholeCredits(targetCredits)),
    maxCredits: Math.max(preferences.maxCredits, wholeCredits(targetCredits)),
  })
  const setMinCredits = (value: number) => {
    const minCredits = wholeCredits(value)
    onChange({ ...preferences, minCredits, maxCredits: Math.max(preferences.maxCredits, minCredits), targetCredits: Math.max(preferences.targetCredits, minCredits) })
  }
  const setMaxCredits = (value: number) => {
    const maxCredits = wholeCredits(value)
    onChange({ ...preferences, maxCredits, minCredits: Math.min(preferences.minCredits, maxCredits), targetCredits: Math.min(preferences.targetCredits, maxCredits) })
  }
  return <section className="preferences-panel" aria-labelledby="preferences-title">
    <div className="section-heading"><div><h2 id="preferences-title">자동 생성 조건</h2><p>필수 조건은 지키고, 나머지는 가능한 만큼 반영합니다.</p></div></div>
    <div className="preset-section">
      <h3>시간표 스타일</h3>
      <div className="preset-grid">{PREFERENCE_PRESETS.map((preset) => <button type="button" key={preset.id} aria-label={preset.label} aria-pressed={activePreset === preset.id} onClick={() => onChange(applyPreferencePreset(preferences, preset.id))}><strong>{preset.label}</strong><small>{preset.description}</small></button>)}</div>
    </div>
    <div className="primary-preference">
      <label><span>목표 학점</span><input type="number" min="1" max="30" value={preferences.targetCredits} onChange={(event) => setTargetCredits(Number(event.target.value))} /></label>
    </div>
    <fieldset className="free-day-field"><legend>공강을 원하는 요일</legend><div>{(['월', '화', '수', '목', '금'] as Day[]).map((day) => <label key={day} className={preferences.preferredFreeDays.includes(day) ? 'checked' : ''}><input type="checkbox" checked={preferences.preferredFreeDays.includes(day)} onChange={() => toggleDay(day)} /><span>{day}</span></label>)}</div></fieldset>
    <fieldset className="free-day-field strict-day-field"><legend>수업을 완전히 제외할 요일</legend><div>{(['월', '화', '수', '목', '금'] as Day[]).map((day) => <label key={day} className={preferences.excludedDays.includes(day) ? 'checked' : ''}><input aria-label={`${day}요일 완전 제외`} type="checkbox" checked={preferences.excludedDays.includes(day)} onChange={() => toggleExcludedDay(day)} /><span>{day}</span></label>)}</div></fieldset>
    <label className="check-row"><input type="checkbox" checked={preferences.minimizeChanges} onChange={(event) => onChange({ ...preferences, minimizeChanges: event.target.checked })} /><span><strong>현재 선택을 최대한 유지</strong><small>잠근 과목은 항상 유지됩니다.</small></span></label>
    <details className="advanced-preferences">
      <summary>세부 조건 조정</summary>
      <p>학점 범위와 시간 기준을 직접 조정합니다.</p>
      <div className="preference-grid">
        <label><span>최소 학점</span><input type="number" min="1" max="30" value={preferences.minCredits} onChange={(event) => setMinCredits(Number(event.target.value))} /></label>
        <label><span>최대 학점</span><input type="number" min="1" max="30" value={preferences.maxCredits} onChange={(event) => setMaxCredits(Number(event.target.value))} /></label>
        <label><span>이 시간 전 피하기</span><input type="time" value={preferences.avoidBefore ?? ''} onChange={(event) => onChange({ ...preferences, avoidBefore: event.target.value || null })} /></label>
        <label><span>이 시간 후 피하기</span><input type="time" value={preferences.avoidAfter ?? ''} onChange={(event) => onChange({ ...preferences, avoidAfter: event.target.value || null })} /></label>
        <label><span>수업 시작 가능 시각</span><input type="time" value={preferences.hardStart ?? ''} onChange={(event) => onChange({ ...preferences, hardStart: event.target.value || null })} /></label>
        <label><span>수업 종료 제한 시각</span><input type="time" value={preferences.hardEnd ?? ''} onChange={(event) => onChange({ ...preferences, hardEnd: event.target.value || null })} /></label>
        <label><span>하루 허용 공강 합계</span><select value={preferences.maxGapMinutes ?? ''} onChange={(event) => onChange({ ...preferences, maxGapMinutes: event.target.value ? Number(event.target.value) : null })}><option value="">제한 없음</option><option value="30">30분</option><option value="60">1시간</option><option value="90">1시간 30분</option><option value="120">2시간</option><option value="180">3시간</option></select></label>
        <label><span>점심 여유</span><select value={preferences.minLunchMinutes} onChange={(event) => onChange({ ...preferences, minLunchMinutes: Number(event.target.value) })}><option value="0">상관없음</option><option value="30">30분</option><option value="60">60분</option><option value="90">90분</option></select></label>
        <label><span>하루 최대 수업</span><select value={preferences.maxDailyMinutes} onChange={(event) => onChange({ ...preferences, maxDailyMinutes: Number(event.target.value) })}><option value="240">4시간</option><option value="300">5시간</option><option value="360">6시간</option><option value="480">8시간</option></select></label>
      </div>
      <label className="range-field"><span><b>빈 시간 줄이기</b><output>{preferences.compactness}%</output></span><input aria-label="빈 시간 줄이기" type="range" min="0" max="100" step="10" value={preferences.compactness} onChange={(event) => onChange({ ...preferences, compactness: Number(event.target.value) })} /></label>
    </details>
  </section>
}
