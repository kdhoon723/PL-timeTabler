import { useCallback, useEffect, useMemo, useReducer, useState } from 'react'
import { loadCatalog } from './api/client'
import { findAlternatives, findConflicts } from './domain/conflicts'
import { computeMetrics } from './domain/metrics'
import { encodeDraft } from './domain/share'
import { timeToMinutes } from './domain/time'
import { draftReducer, loadSavedDraft } from './state/draft'
import type { Candidate, CourseRole, Section } from './types'
import { AppHeader } from './components/AppHeader'
import { ConflictNotice } from './components/ConflictNotice'
import { CourseSearchSheet } from './components/CourseSearchSheet'
import { OptimizerPanel } from './components/OptimizerPanel'
import { PlusIcon, SlidersIcon } from './components/Icons'
import { PreferencesPanel } from './components/PreferencesPanel'
import { RegistrationChecklist } from './components/RegistrationChecklist'
import { RequirementsPage } from './components/RequirementsPage'
import { SectionDetailSheet } from './components/SectionDetailSheet'
import { SelectedCourseList } from './components/SelectedCourseList'
import { TimetableGrid } from './components/TimetableGrid'
import { Toast } from './components/Toast'

export default function App() {
  const [state, dispatch] = useReducer(draftReducer, undefined, () => ({ past: [], present: loadSavedDraft(), future: [] }))
  const [catalog, setCatalog] = useState<Section[]>([])
  const [catalogMeta, setCatalogMeta] = useState<{ version: string; updatedAt: string; offline: boolean } | null>(null)
  const [catalogError, setCatalogError] = useState<string | null>(null)
  const [searchOpen, setSearchOpen] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [showTools, setShowTools] = useState(false)
  const [route, setRoute] = useState(location.pathname)
  const [toast, setToast] = useState<string | null>(null)

  const sectionById = useMemo(() => new Map(catalog.map((section) => [section.id, section])), [catalog])
  const activeSections = useMemo(() => state.present.items.filter((item) => item.role === 'must' || item.role === 'want').map((item) => sectionById.get(item.sectionId)).filter((section): section is Section => !!section), [sectionById, state.present.items])
  const metrics = useMemo(() => computeMetrics(activeSections), [activeSections])
  const conflicts = useMemo(() => findConflicts(state.present.items, sectionById), [sectionById, state.present.items])
  const selectedSection = selectedId ? sectionById.get(selectedId) ?? null : null
  const selectedItem = selectedId ? state.present.items.find((item) => item.sectionId === selectedId) : undefined
  const alternatives = selectedSection ? findAlternatives(selectedSection, catalog, activeSections) : []

  const fetchCatalog = useCallback(() => {
    setCatalogError(null)
    loadCatalog(state.present.semester).then(({ catalog: loaded, offline }) => {
      setCatalog(loaded.sections)
      setCatalogMeta({ version: loaded.dataVersion, updatedAt: loaded.updatedAt, offline })
      const validIds = new Set(loaded.sections.map((section) => section.id))
      const validItems = state.present.items.filter((item) => validIds.has(item.sectionId))
      const removed = state.present.items.length - validItems.length
      if (removed || state.present.dataVersion !== loaded.dataVersion) {
        dispatch({ type: 'LOAD', snapshot: { ...state.present, dataVersion: loaded.dataVersion, items: validItems, updatedAt: new Date().toISOString() } })
        if (removed) setToast(`현재 데이터에서 사라진 ${removed}개 분반을 제외했습니다.`)
      }
    }).catch((error: unknown) => setCatalogError(error instanceof Error ? error.message : '강의 데이터를 불러오지 못했습니다.'))
  }, [state.present])

  useEffect(() => { fetchCatalog() }, []) // initial catalog load only
  useEffect(() => {
    try { localStorage.setItem('pl-timetabler:draft:v1', JSON.stringify(state.present)) } catch { setToast('브라우저 저장 공간이 부족해 자동 저장하지 못했습니다.') }
  }, [state.present])
  useEffect(() => {
    const handler = () => setRoute(location.pathname)
    addEventListener('popstate', handler)
    return () => removeEventListener('popstate', handler)
  }, [])

  const navigate = (path: string) => { history.pushState({}, '', path); setRoute(path); scrollTo({ top: 0, behavior: 'instant' }) }
  const addSection = (section: Section, role: CourseRole = 'want') => {
    const sameCourse = state.present.items.find((item) => sectionById.get(item.sectionId)?.courseCode === section.courseCode && item.role !== 'backup' && item.role !== 'exclude')
    if (sameCourse && role !== 'backup' && role !== 'exclude') dispatch({ type: 'SWAP', fromId: sameCourse.sectionId, toId: section.id })
    else dispatch({ type: 'ADD', item: { sectionId: section.id, role, locked: false } })
    setToast(`${section.name} ${section.sectionCode}분반을 추가했습니다.`)
  }
  const removeSection = () => {
    if (!selectedSection) return
    dispatch({ type: 'REMOVE', sectionId: selectedSection.id }); setSelectedId(null); setToast(`${selectedSection.name}을 삭제했습니다.`)
  }
  const swapSection = (section: Section) => {
    if (!selectedSection) return
    dispatch({ type: 'SWAP', fromId: selectedSection.id, toId: section.id }); setSelectedId(section.id); setToast(`${section.sectionCode}분반으로 교체했습니다.`)
  }
  const applyCandidate = (candidate: Candidate) => { dispatch({ type: 'APPLY', sectionIds: candidate.sectionIds }); setToast('자동 생성 후보를 적용했습니다.'); setShowTools(false) }
  const applyBackup = (section: Section) => { dispatch({ type: 'PATCH_ITEM', sectionId: section.id, patch: { role: 'want' } }); setToast(`${section.name}을 현재 시간표에 적용했습니다.`) }

  const share = async () => {
    const url = new URL(location.origin)
    url.searchParams.set('plan', encodeDraft(state.present))
    try {
      if (navigator.share) await navigator.share({ title: 'PL 시간표', text: '내 시간표를 확인해 보세요.', url: url.toString() })
      else { await navigator.clipboard.writeText(url.toString()); setToast('개인 이수내역 없이 시간표 링크를 복사했습니다.') }
    } catch (error) { if (error instanceof DOMException && error.name === 'AbortError') return; setToast('공유 링크를 만들지 못했습니다.') }
  }
  const exportImage = () => {
    const canvas = document.createElement('canvas'); canvas.width = 1200; canvas.height = 760
    const ctx = canvas.getContext('2d'); if (!ctx) return
    ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, canvas.width, canvas.height); ctx.fillStyle = '#16181D'; ctx.font = '600 32px sans-serif'; ctx.fillText('2026학년도 1학기 시간표', 48, 54)
    const days = ['월', '화', '수', '목', '금']; const start = 8 * 60 + 30; const end = 20 * 60 + 30; const left = 90; const top = 100; const cellWidth = 210; const height = 610
    ctx.font = '500 20px sans-serif'; ctx.textAlign = 'center'; days.forEach((day, index) => ctx.fillText(day, left + index * cellWidth + cellWidth / 2, 90))
    ctx.strokeStyle = '#DCE0E6'; for (let index = 0; index <= days.length; index += 1) { ctx.beginPath(); ctx.moveTo(left + index * cellWidth, top); ctx.lineTo(left + index * cellWidth, top + height); ctx.stroke() }
    for (let minute = start; minute <= end; minute += 60) { const y = top + ((minute - start) / (end - start)) * height; ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(left + days.length * cellWidth, y); ctx.stroke(); ctx.fillStyle = '#555D6B'; ctx.font = '16px sans-serif'; ctx.textAlign = 'right'; ctx.fillText(`${Math.floor(minute / 60)}:${String(minute % 60).padStart(2, '0')}`, left - 12, y + 5) }
    activeSections.forEach((section, sectionIndex) => section.sessions.forEach((session) => { const dayIndex = days.indexOf(session.day); if (dayIndex < 0) return; const y = top + ((timeToMinutes(session.start) - start) / (end - start)) * height; const h = ((timeToMinutes(session.end) - timeToMinutes(session.start)) / (end - start)) * height; ctx.fillStyle = ['#E8EEFC','#E8F3EC','#F2EDF8','#F8EEE8','#E8F2F5','#F5F0E5'][sectionIndex % 6] ?? '#E8EEFC'; ctx.fillRect(left + dayIndex * cellWidth + 3, y + 2, cellWidth - 6, h - 4); ctx.fillStyle = '#16181D'; ctx.textAlign = 'left'; ctx.font = '600 16px sans-serif'; ctx.fillText(section.name.slice(0, 18), left + dayIndex * cellWidth + 12, y + 26); ctx.font = '14px sans-serif'; ctx.fillText(`${session.start} ${session.room ?? ''}`, left + dayIndex * cellWidth + 12, y + 48) }))
    const link = document.createElement('a'); link.download = 'PL-시간표-2026-1.png'; link.href = canvas.toDataURL('image/png'); link.click()
  }

  if (route === '/requirements') return <><RequirementsPage catalog={catalog} onBack={() => navigate('/')} onAddCourse={(section) => { addSection(section, 'must'); navigate('/') }} /><Toast message={toast} onClose={() => setToast(null)} /></>

  return <div className="app-shell">
    <AppHeader credits={metrics.credits} canUndo={!!state.past.length} canRedo={!!state.future.length} onUndo={() => dispatch({ type: 'UNDO' })} onRedo={() => dispatch({ type: 'REDO' })} onShare={share} onNavigate={navigate} />
    {catalogError && <div className="global-error" role="alert"><span>{catalogError}</span><button type="button" onClick={fetchCatalog}>다시 시도</button></div>}
    {catalogMeta && <div className="data-status"><span>{catalogMeta.offline ? '저장된 데이터 사용 중' : '최신 데이터 연결됨'}</span><span>2026-1 · {catalogMeta.updatedAt} 기준</span></div>}
    <main className="editor-layout">
      <aside className="desktop-search"><button type="button" className="primary-button full-button" onClick={() => setSearchOpen(true)}><PlusIcon />과목 추가</button><SelectedCourseList items={state.present.items} sectionById={sectionById} onSelect={(section) => setSelectedId(section.id)} /></aside>
      <div className="editor-main"><ConflictNotice conflicts={conflicts} onOpen={setSelectedId} /><TimetableGrid sections={activeSections} conflicts={conflicts} lockedIds={new Set(state.present.items.filter((item) => item.locked).map((item) => item.sectionId))} onSelect={(section) => setSelectedId(section.id)} />
        <div className="mobile-summary"><SelectedCourseList items={state.present.items} sectionById={sectionById} onSelect={(section) => setSelectedId(section.id)} /></div>
      </div>
      <aside className={`tools-panel ${showTools ? 'mobile-open' : ''}`}><div className="mobile-tools-header"><h2>자동 생성과 준비</h2><button type="button" onClick={() => setShowTools(false)}>닫기</button></div><PreferencesPanel preferences={state.present.preferences} onChange={(preferences) => dispatch({ type: 'PREFERENCES', preferences })} /><OptimizerPanel draft={state.present} onApply={applyCandidate} /><RegistrationChecklist items={state.present.items} sectionById={sectionById} onApplyBackup={applyBackup} onMessage={setToast} /><section className="export-panel"><h2>내보내기</h2><div><button type="button" className="secondary-button" onClick={exportImage}>PNG 저장</button><button type="button" className="secondary-button" onClick={() => print()}>인쇄·PDF</button></div></section><p className="source-copy">대진대학교 공개 개설과목 · 데이터 {catalogMeta?.version.slice(0, 12) ?? '확인 중'}</p></aside>
    </main>
    <div className="mobile-action-bar"><button type="button" className="secondary-button" onClick={() => setShowTools(true)}><SlidersIcon />자동 생성</button><button type="button" className="primary-button" onClick={() => setSearchOpen(true)}><PlusIcon />과목 추가</button></div>
    <CourseSearchSheet open={searchOpen} sections={catalog} items={state.present.items} onClose={() => setSearchOpen(false)} onAdd={addSection} />
    <SectionDetailSheet section={selectedSection} role={selectedItem?.role ?? 'want'} locked={selectedItem?.locked ?? false} alternatives={alternatives} onClose={() => setSelectedId(null)} onRole={(role) => selectedSection && dispatch({ type: 'PATCH_ITEM', sectionId: selectedSection.id, patch: { role } })} onLock={() => selectedSection && dispatch({ type: 'PATCH_ITEM', sectionId: selectedSection.id, patch: { locked: !selectedItem?.locked } })} onRemove={removeSection} onSwap={swapSection} />
    <Toast message={toast} onClose={() => setToast(null)} onUndo={state.past.length ? () => dispatch({ type: 'UNDO' }) : undefined} />
  </div>
}
