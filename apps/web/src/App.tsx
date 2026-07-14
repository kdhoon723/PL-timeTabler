import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react'
import { loadAuthSession, loadCatalog, loadCommonRules, loadCourseStats, loadCurrentUser, loadDepartmentSources, loadMajorRequiredCourses, updateCurrentUser } from './api/client'
import { findAlternatives, findConflicts } from './domain/conflicts'
import { diffCandidate } from './domain/candidateDiff'
import { optimizationDraftFingerprint } from './domain/optimizationDraft'
import { computeMetrics } from './domain/metrics'
import { encodeDraft } from './domain/share'
import { exportTimetablePng } from './domain/exportImage'
import { completeOnboardingWithoutProfile, hasCompletedOnboarding, loadAcademicProfile, saveAcademicProfile } from './domain/profile'
import { draftReducer, itemsWithAppliedBackup, itemsWithCourseRole, loadSavedDraft, planItemsForCandidate } from './state/draft'
import type { AcademicProfile, AuthSession, Candidate, CommonRules, CourseRole, CourseStats, DepartmentSource, MajorRequiredCourses, Section, UserInfo } from './types'
import { AppHeader } from './components/AppHeader'
import { ApplicationListSheet } from './components/ApplicationListSheet'
import { AuthSheet } from './components/AuthSheet'
import { CandidatePreviewBar } from './components/CandidatePreviewBar'
import { CandidateCourseBasket } from './components/CandidateCourseBasket'
import { ConflictNotice } from './components/ConflictNotice'
import { CourseSearchSheet, type CourseSearchDestination, type CourseSearchMode } from './components/CourseSearchSheet'
import { CourseEntryPanel } from './components/CourseEntryPanel'
import { Onboarding } from './components/Onboarding'
import { OptimizerPanel } from './components/OptimizerPanel'
import { PlusIcon, SlidersIcon } from './components/Icons'
import { PreferencesPanel } from './components/PreferencesPanel'
import { RequiredCourseSheet } from './components/RequiredCourseSheet'
import { RequirementsPage } from './components/RequirementsPage'
import { ReviewSheet } from './components/ReviewSheet'
import { SectionDetailSheet } from './components/SectionDetailSheet'
import { SharedTimetablePage } from './components/SharedTimetablePage'
import { SelectedCourseList } from './components/SelectedCourseList'
import { TimetableGrid } from './components/TimetableGrid'
import { Toast } from './components/Toast'
import { MyPage } from './components/MyPage'

function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => typeof matchMedia === 'function' && matchMedia(query).matches)
  useEffect(() => {
    if (typeof matchMedia !== 'function') return
    const media = matchMedia(query)
    const update = () => setMatches(media.matches)
    update()
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [query])
  return matches
}

export default function App() {
  const [state, dispatch] = useReducer(draftReducer, undefined, () => ({ past: [], present: loadSavedDraft(), future: [] }))
  const [catalog, setCatalog] = useState<Section[]>([])
  const [catalogMeta, setCatalogMeta] = useState<{ updatedAt: string; offline: boolean } | null>(null)
  const [catalogError, setCatalogError] = useState<string | null>(null)
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchMode, setSearchMode] = useState<CourseSearchMode>('ALL')
  const [searchDestination, setSearchDestination] = useState<CourseSearchDestination>('TIMETABLE')
  const [requiredOpen, setRequiredOpen] = useState(false)
  const [applicationListOpen, setApplicationListOpen] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [candidatePreview, setCandidatePreview] = useState<{ candidate: Candidate; generationFingerprint: string } | null>(null)
  const [showTools, setShowTools] = useState(false)
  const [route, setRoute] = useState(location.pathname)
  const [toast, setToast] = useState<string | null>(null)
  const [toastUndoable, setToastUndoable] = useState(false)
  const [profile, setProfile] = useState<AcademicProfile | null>(() => loadAcademicProfile())
  const [onboardingOpen, setOnboardingOpen] = useState(() => !hasCompletedOnboarding() && !new URLSearchParams(location.search).has('plan'))
  const [profileEditorOpen, setProfileEditorOpen] = useState(false)
  const [authOpen, setAuthOpen] = useState(false)
  const [authSession, setAuthSession] = useState<AuthSession>({ available: false, authenticated: false, studentNumber: null, expiresAt: null })
  const [, setCurrentUser] = useState<UserInfo | null>(null)
  const [sessionExpired, setSessionExpired] = useState(false)
  const [reviewSection, setReviewSection] = useState<Section | null>(null)
  const [courseStats, setCourseStats] = useState<ReadonlyMap<string, CourseStats>>(new Map())
  const [commonRules, setCommonRules] = useState<CommonRules | null>(null)
  const [departments, setDepartments] = useState<DepartmentSource[]>([])
  const [majorRequired, setMajorRequired] = useState<MajorRequiredCourses | null>(null)
  const isDesktopTools = useMediaQuery('(min-width: 768px)')
  const isDesktopDrag = useMediaQuery('(min-width: 1200px)')
  const presentRef = useRef(state.present)
  const toolsDialogRef = useRef<HTMLDialogElement>(null)
  const toolsCloseRef = useRef<HTMLButtonElement>(null)
  const toolsTriggerRef = useRef<HTMLButtonElement>(null)
  const showToolsRef = useRef(showTools)
  const toolsHistoryRef = useRef(false)
  const previewBarRef = useRef<HTMLElement>(null)
  const focusPreviewAfterToolsCloseRef = useRef(false)
  presentRef.current = state.present
  showToolsRef.current = showTools

  const sectionById = useMemo(() => new Map(catalog.map((section) => [section.id, section])), [catalog])
  const draftFingerprint = useMemo(() => optimizationDraftFingerprint(state.present), [state.present])
  const validCandidatePreview = candidatePreview?.generationFingerprint === draftFingerprint ? candidatePreview : null
  const activeSections = useMemo(() => state.present.items.filter((item) => item.role === 'must' || item.role === 'want').map((item) => sectionById.get(item.sectionId)).filter((section): section is Section => !!section), [sectionById, state.present.items])
  const metrics = useMemo(() => computeMetrics(activeSections), [activeSections])
  const conflicts = useMemo(() => findConflicts(state.present.items, sectionById), [sectionById, state.present.items])
  const previewDiff = useMemo(() => validCandidatePreview ? diffCandidate(validCandidatePreview.candidate.sectionIds, state.present.items, sectionById) : null, [sectionById, state.present.items, validCandidatePreview])
  const previewItems = useMemo(() => validCandidatePreview ? planItemsForCandidate(validCandidatePreview.candidate.sectionIds, state.present.items, sectionById) : null, [sectionById, state.present.items, validCandidatePreview])
  const previewConflicts = useMemo(() => previewItems ? findConflicts(previewItems, sectionById) : conflicts, [conflicts, previewItems, sectionById])
  const previewStatusById = useMemo(() => previewDiff ? new Map(previewDiff.previewSections.map(({ section, state: previewState }) => [section.id, previewState])) : undefined, [previewDiff])
  const gridSections = previewDiff ? previewDiff.previewSections.map(({ section }) => section) : activeSections
  const selectedSection = selectedId ? sectionById.get(selectedId) ?? null : null
  const selectedItem = selectedId ? state.present.items.find((item) => item.sectionId === selectedId) : undefined
  const alternatives = selectedSection ? findAlternatives(selectedSection, catalog, activeSections) : []
  const professorLockAvailable = !!selectedSection?.professor && catalog.some((section) => section.id !== selectedSection.id && section.courseCode === selectedSection.courseCode && section.professor === selectedSection.professor)
  const dragAlternativesById = useMemo(() => new Map(activeSections.map((section) => {
    const item = state.present.items.find((candidate) => candidate.sectionId === section.id)
    const candidates = findAlternatives(section, catalog, activeSections)
    return [section.id, item?.professorLocked ? candidates.filter((candidate) => candidate.professor === section.professor) : candidates]
  })), [activeSections, catalog, state.present.items])
  const showToast = useCallback((message: string, undoable = false) => {
    setToast(message)
    setToastUndoable(undoable)
  }, [])
  const handleUserChange = useCallback((user: UserInfo | null) => {
    setCurrentUser(user)
    if (!user) {
      setAuthSession((current) => ({ available: current.available, authenticated: false, studentNumber: null, expiresAt: null }))
      return
    }
    if (user.department && user.grade) {
      setProfile((current) => ({
        schemaVersion: 2,
        department: user.department!,
        currentGrade: user.grade as 1 | 2 | 3 | 4,
        academicBasis: current?.academicBasis ?? null,
        updatedAt: new Date().toISOString(),
      }))
    }
  }, [])
  const focusPreviewBar = useCallback(() => requestAnimationFrame(() => requestAnimationFrame(() => {
    previewBarRef.current?.scrollIntoView?.({ block: 'start' })
    previewBarRef.current?.focus()
  })), [])

  const fetchCatalog = useCallback(() => {
    setCatalogError(null)
    loadCatalog(presentRef.current.semester).then(({ catalog: loaded, offline }) => {
      setCandidatePreview(null)
      setCatalog(loaded.sections)
      setCatalogMeta({ updatedAt: loaded.updatedAt, offline })
      const validIds = new Set(loaded.sections.map((section) => section.id))
      const current = presentRef.current
      const validItems = current.items.filter((item) => validIds.has(item.sectionId))
      const removed = current.items.length - validItems.length
      if (removed || current.dataVersion !== loaded.dataVersion) {
        dispatch({ type: 'CATALOG', dataVersion: loaded.dataVersion, validIds })
        if (removed) showToast(`현재 데이터에서 사라진 ${removed}개 분반을 제외했습니다.`)
      }
    }).catch((error: unknown) => setCatalogError(error instanceof Error ? error.message : '강의 데이터를 불러오지 못했습니다.'))
  }, [showToast])

  useEffect(() => { fetchCatalog() }, []) // initial catalog load only
  useEffect(() => {
    loadAuthSession().then(async (session) => {
      setAuthSession(session)
      if (session.authenticated) {
        const user = await loadCurrentUser()
        setCurrentUser(user)
      }
    }).catch(() => { /* guest mode remains available */ })
    loadCourseStats().then((items) => setCourseStats(new Map(items.map((item) => [item.courseCode, item])))).catch(() => { /* search remains available without review aggregates */ })
    loadCommonRules().then(setCommonRules).catch(() => { /* requirements UI shows its fallback state */ })
    loadDepartmentSources().then((value) => setDepartments(value.departments)).catch(() => { /* profile can be edited after a retry/reload */ })
    loadMajorRequiredCourses().then(setMajorRequired).catch(() => { /* never guess major-required courses */ })
  }, [])
  useEffect(() => {
    const expired = () => {
      setAuthSession((current) => ({ available: current.available, authenticated: false, studentNumber: null, expiresAt: null }))
      setCurrentUser(null)
      setSessionExpired(true)
    }
    addEventListener('timetabler:session-expired', expired)
    return () => removeEventListener('timetabler:session-expired', expired)
  }, [])
  useEffect(() => {
    try { localStorage.setItem('pl-timetabler:draft:v1', JSON.stringify(state.present)) } catch { showToast('브라우저 저장 공간이 부족해 자동 저장하지 못했습니다.') }
  }, [showToast, state.present])
  useEffect(() => {
    const handler = () => {
      if (showToolsRef.current) {
        setShowTools(false)
        toolsHistoryRef.current = false
        const focusPreview = focusPreviewAfterToolsCloseRef.current
        focusPreviewAfterToolsCloseRef.current = false
        if (focusPreview) focusPreviewBar()
        else requestAnimationFrame(() => toolsTriggerRef.current?.focus())
      }
      setRoute(location.pathname)
    }
    addEventListener('popstate', handler)
    return () => removeEventListener('popstate', handler)
  }, [focusPreviewBar])
  useEffect(() => {
    const dialog = toolsDialogRef.current
    if (!dialog || isDesktopTools) return
    if (showTools && !dialog.open) {
      dialog.showModal()
      requestAnimationFrame(() => toolsCloseRef.current?.focus())
    } else if (!showTools && dialog.open) dialog.close()
  }, [isDesktopTools, showTools])
  useEffect(() => {
    if (candidatePreview && candidatePreview.generationFingerprint !== draftFingerprint) {
      setCandidatePreview(null)
      showToast('시간표 조건이 바뀌어 이전 후보를 닫았습니다. 새 후보를 만들어 주세요.')
    }
  }, [candidatePreview, draftFingerprint, showToast])
  useEffect(() => {
    const handleShortcut = (event: KeyboardEvent) => {
      if (!(event.ctrlKey || event.metaKey) || event.altKey || event.key.toLocaleLowerCase() !== 'z') return
      const target = event.target
      if (target instanceof HTMLElement && (target.matches('input, textarea, select') || target.isContentEditable || !!target.closest('[contenteditable="true"]'))) return
      if (event.shiftKey) {
        if (!state.future.length) return
        event.preventDefault()
        dispatch({ type: 'REDO' })
      } else {
        if (!state.past.length) return
        event.preventDefault()
        dispatch({ type: 'UNDO' })
      }
    }
    addEventListener('keydown', handleShortcut)
    return () => removeEventListener('keydown', handleShortcut)
  }, [state.future.length, state.past.length])

  const navigate = (path: string) => { history.pushState({}, '', path); setRoute(path); scrollTo({ top: 0, behavior: 'instant' }) }
  const openCourseSearch = (mode: CourseSearchMode = 'ALL', destination: CourseSearchDestination = 'TIMETABLE') => {
    setSearchMode(mode)
    setSearchDestination(destination)
    setSearchOpen(true)
  }
  const editProfileFromRequired = () => {
    setRequiredOpen(false)
    requestAnimationFrame(() => setProfileEditorOpen(true))
  }
  const openTools = (trigger: HTMLButtonElement) => {
    toolsTriggerRef.current = trigger
    if (!toolsHistoryRef.current) {
      history.pushState({ ...history.state, plTimetablerOverlay: 'tools' }, '', location.href)
      toolsHistoryRef.current = true
    }
    setShowTools(true)
  }
  const closeTools = (focusTarget: 'trigger' | 'preview' = 'trigger') => {
    focusPreviewAfterToolsCloseRef.current = focusTarget === 'preview'
    if (toolsHistoryRef.current && history.state?.plTimetablerOverlay === 'tools') history.back()
    else {
      setShowTools(false)
      toolsHistoryRef.current = false
      if (focusTarget === 'preview') focusPreviewBar()
      else requestAnimationFrame(() => toolsTriggerRef.current?.focus())
    }
  }
  const previewCandidate = (candidate: Candidate, generationFingerprint: string) => {
    if (generationFingerprint !== draftFingerprint) {
      showToast('시간표 조건이 바뀌어 이 후보를 미리 볼 수 없습니다. 새 후보를 만들어 주세요.')
      return
    }
    setCandidatePreview({ candidate, generationFingerprint })
    setSelectedId(null)
    if (!isDesktopTools && showTools) closeTools('preview')
    else focusPreviewBar()
  }
  const cancelCandidatePreview = () => {
    setCandidatePreview(null)
    requestAnimationFrame(() => document.getElementById('timetable-title')?.focus())
  }
  const addSection = (section: Section, role: CourseRole = 'want') => {
    const excludedSameCourse = state.present.items.filter((item) => item.role === 'exclude' && sectionById.get(item.sectionId)?.courseCode === section.courseCode)
    if (excludedSameCourse.length) {
      dispatch({ type: 'ITEMS', items: [...state.present.items.filter((item) => !excludedSameCourse.includes(item)), { sectionId: section.id, role, locked: false, professorLocked: false }] })
      showToast(`${section.name} ${section.sectionCode}분반을 추가했습니다.`, true)
      return
    }
    const sameCourse = state.present.items.find((item) => sectionById.get(item.sectionId)?.courseCode === section.courseCode && item.role !== 'backup' && item.role !== 'exclude')
    if (sameCourse && role !== 'backup' && role !== 'exclude') {
      const previousSection = sectionById.get(sameCourse.sectionId)
      dispatch({ type: 'ITEMS', items: state.present.items.map((item) => item.sectionId === sameCourse.sectionId ? { ...item, sectionId: section.id, role: role === 'must' || item.role === 'must' ? 'must' : item.role, professorLocked: item.professorLocked && previousSection?.professor === section.professor } : item) })
    } else if (state.present.items.some((item) => item.sectionId === section.id)) {
      dispatch({ type: 'ITEMS', items: itemsWithCourseRole(section.id, role, state.present.items, sectionById) })
    } else dispatch({ type: 'ADD', item: { sectionId: section.id, role, locked: false, professorLocked: false } })
    showToast(`${section.name} ${section.sectionCode}분반을 추가했습니다.`, true)
  }
  const removeSection = () => {
    if (!selectedSection) return
    dispatch({ type: 'REMOVE', sectionId: selectedSection.id }); setSelectedId(null); showToast(`${selectedSection.name}을 삭제했습니다.`, true)
  }
  const swapSection = (section: Section) => {
    if (!selectedSection) return
    dispatch({ type: 'SWAP', fromId: selectedSection.id, toId: section.id }); setSelectedId(section.id); showToast(`${section.sectionCode}분반으로 교체했습니다.`, true)
  }
  const dragReplaceSection = (source: Section, replacement: Section) => {
    const sourceItem = state.present.items.find((item) => item.sectionId === source.id)
    const validReplacement = dragAlternativesById.get(source.id)?.some((section) => section.id === replacement.id)
    if (!isDesktopDrag || validCandidatePreview || !sourceItem || sourceItem.locked || !validReplacement) return
    dispatch({ type: 'SWAP', fromId: source.id, toId: replacement.id })
    setSelectedId(null)
    showToast(`${source.name} ${source.sectionCode}분반을 ${replacement.sectionCode}분반으로 교체했습니다.`, true)
  }
  const applyCandidate = () => {
    if (!candidatePreview || candidatePreview.generationFingerprint !== draftFingerprint) {
      setCandidatePreview(null)
      showToast('시간표 조건이 바뀌어 이전 후보를 적용하지 않았습니다. 새 후보를 만들어 주세요.')
      return
    }
    dispatch({ type: 'APPLY', items: planItemsForCandidate(candidatePreview.candidate.sectionIds, state.present.items, sectionById) })
    setCandidatePreview(null)
    showToast('자동 생성 후보를 적용했습니다.', true)
    if (showTools) closeTools()
  }
  const applyBackup = (section: Section) => { dispatch({ type: 'ITEMS', items: itemsWithAppliedBackup(section.id, state.present.items, sectionById) }); showToast(`${section.name}을 현재 시간표에 적용했습니다.`, true) }
  const removePassiveCourse = (section: Section) => {
    const courseItems = state.present.items.filter((item) => sectionById.get(item.sectionId)?.courseCode === section.courseCode && (item.role === 'backup' || item.role === 'exclude'))
    dispatch({ type: 'ITEMS', items: state.present.items.filter((item) => !courseItems.includes(item)) })
    showToast(`${section.name}을 자동완성 목록에서 삭제했습니다.`, true)
  }
  const openCandidateSearch = () => {
    if (!isDesktopTools && showTools) {
      closeTools()
      window.setTimeout(() => openCourseSearch('ALL', 'CANDIDATES'), 0)
      return
    }
    openCourseSearch('ALL', 'CANDIDATES')
  }

  const share = async () => {
    const url = new URL(location.origin)
    url.searchParams.set('plan', encodeDraft(state.present))
    try {
      if (navigator.share) await navigator.share({ title: 'PL 시간표', text: '내 시간표를 확인해 보세요.', url: url.toString() })
      else { await navigator.clipboard.writeText(url.toString()); showToast('개인 이수내역 없이 시간표 링크를 복사했습니다.') }
    } catch (error) { if (error instanceof DOMException && error.name === 'AbortError') return; showToast('공유 링크를 만들지 못했습니다.') }
  }
  const exportImage = () => exportTimetablePng(activeSections, state.present.semester)

  const refreshCourseStats = () => loadCourseStats().then((items) => setCourseStats(new Map(items.map((item) => [item.courseCode, item])))).catch(() => undefined)
  const handleAuthSession = (session: AuthSession) => {
    setAuthSession(session)
    if (!session.authenticated) { setCurrentUser(null); return }
    setSessionExpired(false)
    loadCurrentUser().then((user) => {
      setCurrentUser(user)
      if (!user.profileCompleted) {
        showToast('이름과 학적정보, 개인정보 동의를 등록해 주세요.')
        navigate('/mypage')
      }
    }).catch(() => undefined)
  }

  const completeProfile = (next: AcademicProfile) => {
    try { saveAcademicProfile(next) } catch { showToast('학적 정보를 브라우저에 저장하지 못했습니다.') }
    setProfile(next); setCandidatePreview(null); setOnboardingOpen(false); setProfileEditorOpen(false); showToast(`${next.department} 기준을 적용했습니다.`)
    if (authSession.authenticated) updateCurrentUser({
      grade: next.currentGrade,
      department: next.department,
      admissionYear: next.academicBasis?.admissionYear ?? null,
      entryType: next.academicBasis?.entryType ?? null,
      studentType: next.academicBasis?.studentType ?? null,
      sectionGroup: next.academicBasis?.sectionGroup ?? null,
    }).then(setCurrentUser).catch(() => showToast('브라우저에는 저장했지만 계정정보 동기화에 실패했습니다.'))
  }
  const skipOnboarding = () => {
    try { completeOnboardingWithoutProfile() } catch { /* the current visit can still continue */ }
    setOnboardingOpen(false)
  }

  const authNotice = sessionExpired && <div className="session-expired-notice" role="alert"><span>로그인 세션이 만료되었습니다. 다시 로그인해 주세요.</span><button type="button" onClick={() => setAuthOpen(true)}>다시 로그인</button></div>
  if (route === '/requirements') return <>{authNotice}<RequirementsPage catalog={catalog} profile={profile} majorRequired={majorRequired} authenticated={authSession.authenticated} onBack={() => navigate('/')} onAddCourse={(section) => { addSection(section, 'must'); navigate('/') }} /><AuthSheet open={authOpen} session={authSession} onSession={handleAuthSession} onClose={() => setAuthOpen(false)} /><Toast message={toast} onClose={() => setToast(null)} /></>
  if (route === '/mypage') return <>{authNotice}{authSession.authenticated ? <MyPage currentDraft={state.present} departments={departments} onBack={() => navigate('/')} onLoadTimetable={(draft) => { dispatch({ type: 'LOAD', snapshot: draft }); navigate('/'); showToast('저장한 시간표를 불러왔습니다.') }} onUserChange={handleUserChange} onMessage={showToast} /> : <main className="status-page"><h1>로그인이 필요합니다.</h1><p>시간표 저장, 이수과목과 리뷰는 학교 이메일 로그인 후 이용할 수 있습니다.</p><button type="button" className="primary-button" onClick={() => setAuthOpen(true)}>학교 이메일 로그인</button><button type="button" className="text-button" onClick={() => navigate('/')}>시간표로 돌아가기</button></main>}<AuthSheet open={authOpen} session={authSession} onSession={handleAuthSession} onClose={() => setAuthOpen(false)} /><Toast message={toast} onClose={() => setToast(null)} /></>
  const sharedCode = route.startsWith('/shared/') ? decodeURIComponent(route.slice('/shared/'.length)) : null
  if (sharedCode) return <><SharedTimetablePage code={sharedCode} onBack={() => navigate('/')} onLoad={(draft) => { dispatch({ type: 'LOAD', snapshot: draft }); navigate('/'); showToast('공유 시간표를 편집기로 복사했습니다.') }} /><Toast message={toast} onClose={() => setToast(null)} /></>
  if (route !== '/') return <main className="status-page"><h1>페이지를 찾을 수 없습니다.</h1><p>주소가 올바른지 확인해 주세요.</p><button type="button" className="primary-button" onClick={() => navigate('/')}>시간표로 이동</button></main>

  const candidateBasket = () => <CandidateCourseBasket items={state.present.items} sectionById={sectionById} onAdd={openCandidateSearch} onPromote={(section) => addSection(section, 'want')} onRemove={removePassiveCourse} />
  const toolsContent = <>{!isDesktopDrag && candidateBasket()}<PreferencesPanel preferences={state.present.preferences} onChange={(preferences) => dispatch({ type: 'PREFERENCES', preferences })} /><OptimizerPanel draft={state.present} draftFingerprint={draftFingerprint} sections={catalog} onPreview={previewCandidate} /></>
  const courseEntry = (compact = false) => <CourseEntryPanel compact={compact} profile={profile} onRequired={() => setRequiredOpen(true)} onEditProfile={() => setProfileEditorOpen(true)} onSearch={() => openCourseSearch()} />

  return <div className="app-shell">
    {authNotice}
    <AppHeader credits={metrics.credits} profile={profile} authSession={authSession} canUndo={!!state.past.length} canRedo={!!state.future.length} applicationCount={activeSections.length} onUndo={() => dispatch({ type: 'UNDO' })} onRedo={() => dispatch({ type: 'REDO' })} onShare={share} onApplicationList={() => setApplicationListOpen(true)} onNavigate={navigate} onProfile={() => setProfileEditorOpen(true)} onAccount={() => authSession.authenticated ? navigate('/mypage') : setAuthOpen(true)} />
    {catalogError && <div className="global-error" role="alert"><span>{catalogError}</span><button type="button" onClick={fetchCatalog}>다시 시도</button></div>}
    {catalogMeta?.offline && <div className="data-status" role="status"><strong>저장된 데이터 사용 중</strong><span>{catalogMeta.updatedAt} 갱신본 · 연결 복구 후 자동 확인</span></div>}
    <main className="editor-layout">
      <aside className="desktop-search">{courseEntry()}<SelectedCourseList items={state.present.items} sectionById={sectionById} onSelect={(section) => setSelectedId(section.id)} />{isDesktopDrag && candidateBasket()}</aside>
      <div className="editor-main"><div className="mobile-course-entry">{courseEntry(true)}</div>{activeSections.length > 0 && <button type="button" className="application-summary-bar" onClick={() => setApplicationListOpen(true)}><span>신청 목록 보기</span><strong>{activeSections.length}개 · {metrics.credits}학점</strong></button>}<ConflictNotice conflicts={validCandidatePreview ? previewConflicts : conflicts} previewReadOnly={!!validCandidatePreview} onOpen={setSelectedId} />{validCandidatePreview && previewDiff && <CandidatePreviewBar candidate={validCandidatePreview.candidate} diff={previewDiff} containerRef={previewBarRef} onCancel={cancelCandidatePreview} onApply={applyCandidate} />}<TimetableGrid sections={gridSections} conflicts={validCandidatePreview ? previewConflicts : conflicts} lockedIds={new Set(state.present.items.filter((item) => item.locked).map((item) => item.sectionId))} professorLockedIds={new Set(state.present.items.filter((item) => item.professorLocked).map((item) => item.sectionId))} onSelect={(section) => setSelectedId(section.id)} previewStatusById={previewStatusById} dragEnabled={isDesktopDrag && !validCandidatePreview} dragAlternativesById={dragAlternativesById} onReplace={dragReplaceSection} />
        <div className="mobile-summary"><SelectedCourseList items={state.present.items} sectionById={sectionById} onSelect={(section) => setSelectedId(section.id)} /></div>
      </div>
      {isDesktopTools ? <aside className="tools-panel" aria-label="자동완성">{toolsContent}</aside> : <dialog className="tools-dialog" ref={toolsDialogRef} aria-labelledby="tools-dialog-title" onCancel={(event) => { event.preventDefault(); closeTools() }}><div className="mobile-tools-header"><h2 id="tools-dialog-title">자동완성</h2><button ref={toolsCloseRef} type="button" onClick={() => closeTools()}>닫기</button></div>{toolsContent}</dialog>}
    </main>
    <div className="mobile-action-bar"><button type="button" className="secondary-button" onClick={(event) => openTools(event.currentTarget)}><SlidersIcon />자동완성</button><button type="button" className="primary-button" onClick={() => openCourseSearch()}><PlusIcon />과목 찾기</button></div>
    <CourseSearchSheet open={searchOpen} initialMode={searchMode} destination={searchDestination} sections={catalog} items={state.present.items} profile={profile} courseStats={courseStats} onClose={() => setSearchOpen(false)} onAdd={addSection} onReviews={(section) => { setSearchOpen(false); requestAnimationFrame(() => setReviewSection(section)) }} />
    <RequiredCourseSheet open={requiredOpen} profile={profile} rules={commonRules} majorRequired={majorRequired} catalog={catalog} items={state.present.items} sectionById={sectionById} onClose={() => setRequiredOpen(false)} onEditProfile={editProfileFromRequired} onAddRequired={(section) => addSection(section, 'must')} />
    <ApplicationListSheet open={applicationListOpen} items={state.present.items} sectionById={sectionById} onApplyBackup={applyBackup} onMessage={(message) => showToast(message)} onExportPng={exportImage} onExportPdf={() => print()} onClose={() => setApplicationListOpen(false)} />
    <SectionDetailSheet section={selectedSection} role={selectedItem?.role ?? 'want'} locked={selectedItem?.locked ?? false} professorLocked={selectedItem?.professorLocked ?? false} professorLockAvailable={professorLockAvailable} alternatives={alternatives} onClose={() => setSelectedId(null)} onRole={(role) => selectedSection && dispatch({ type: 'ITEMS', items: itemsWithCourseRole(selectedSection.id, role, state.present.items, sectionById) })} onAdjustmentMode={(mode) => selectedSection && dispatch({ type: 'PATCH_ITEM', sectionId: selectedSection.id, patch: { locked: mode === 'SECTION', professorLocked: mode === 'PROFESSOR' } })} onRemove={removeSection} onSwap={swapSection} />
    {(onboardingOpen || profileEditorOpen) && <Onboarding departments={departments} initialProfile={profile} mode={profileEditorOpen ? 'EDIT' : 'FIRST_RUN'} authAvailable={authSession.available} onComplete={completeProfile} onSkip={profileEditorOpen ? () => setProfileEditorOpen(false) : skipOnboarding} onLogin={() => setAuthOpen(true)} />}
    <ReviewSheet section={reviewSection} authSession={authSession} onClose={() => setReviewSection(null)} onLogin={() => { setReviewSection(null); setAuthOpen(true) }} onChanged={refreshCourseStats} />
    <AuthSheet open={authOpen} session={authSession} onSession={handleAuthSession} onClose={() => setAuthOpen(false)} />
    <Toast message={toast} onClose={() => setToast(null)} onUndo={toastUndoable && state.past.length ? () => { dispatch({ type: 'UNDO' }); setToast(null); setToastUndoable(false) } : undefined} />
  </div>
}
