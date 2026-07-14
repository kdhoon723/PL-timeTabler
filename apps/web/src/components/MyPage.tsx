import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  copySavedTimetable,
  createCompletedCourse,
  createPrivacyConsent,
  createSavedTimetable,
  createTimetableShare,
  deleteCompletedCourse,
  deleteCourseReview,
  deleteCurrentUser,
  deleteSavedTimetable,
  importTimetableCourses,
  loadCompletedCourses,
  loadCurrentUser,
  loadMyReviews,
  loadPrivacyConsents,
  loadSavedTimetables,
  logoutAuthSession,
  setSavedTimetableFavorite,
  updateCompletedCourse,
  updateCurrentUser,
  updateSavedTimetable,
  updateSavedTimetableSections,
} from '../api/client'
import { saveAcademicProfile } from '../domain/profile'
import type {
  CompletedCourse,
  CompletedCourseStatus,
  CourseReview,
  DepartmentSource,
  DraftSnapshot,
  PrivacyConsent,
  SavedTimetable,
  UserInfo,
} from '../types'

interface Props {
  currentDraft: DraftSnapshot
  departments: DepartmentSource[]
  onBack: () => void
  onLoadTimetable: (draft: DraftSnapshot) => void
  onUserChange: (user: UserInfo | null) => void
  onMessage: (message: string) => void
}

const EMPTY_SUMMARY = { totalCredits: 0, majorCredits: 0, liberalCredits: 0, areaCredits: {} as Record<string, number> }

export function MyPage({ currentDraft, departments, onBack, onLoadTimetable, onUserChange, onMessage }: Props) {
  const [user, setUser] = useState<UserInfo | null>(null)
  const [timetables, setTimetables] = useState<SavedTimetable[]>([])
  const [completed, setCompleted] = useState<CompletedCourse[]>([])
  const [summary, setSummary] = useState(EMPTY_SUMMARY)
  const [reviews, setReviews] = useState<CourseReview[]>([])
  const [consents, setConsents] = useState<PrivacyConsent[]>([])
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [favoriteOnly, setFavoriteOnly] = useState(false)
  const [timetableName, setTimetableName] = useState('내 시간표')
  const [names, setNames] = useState<Record<string, string>>({})
  const [name, setName] = useState('')
  const [grade, setGrade] = useState(1)
  const [department, setDepartment] = useState('')
  const [consentChecked, setConsentChecked] = useState(false)
  const [deleteConfirmation, setDeleteConfirmation] = useState('')
  const [editingCourseId, setEditingCourseId] = useState<string | null>(null)
  const [courseName, setCourseName] = useState('')
  const [credits, setCredits] = useState(3)
  const [category, setCategory] = useState('전공')
  const [area, setArea] = useState('')
  const [semester, setSemester] = useState('')
  const [courseStatus, setCourseStatus] = useState<CompletedCourseStatus>('COMPLETED')

  const refresh = useCallback(async () => {
    const [account, saved, completedResult, myReviews, consentHistory] = await Promise.all([
      loadCurrentUser(), loadSavedTimetables(), loadCompletedCourses(), loadMyReviews(), loadPrivacyConsents(),
    ])
    setUser(account); onUserChange(account)
    setName(account.name ?? ''); setGrade(account.grade ?? 1); setDepartment(account.department ?? '')
    setTimetables(saved); setNames(Object.fromEntries(saved.map((item) => [item.id, item.name])))
    setCompleted(completedResult.completedCourses); setSummary(completedResult.creditSummary)
    setReviews(myReviews); setConsents(consentHistory)
  }, [onUserChange])

  useEffect(() => { refresh().catch((caught) => setError(caught instanceof Error ? caught.message : '마이페이지를 불러오지 못했습니다.')) }, [refresh])
  const visibleTimetables = favoriteOnly ? timetables.filter((item) => item.favorite) : timetables
  const semesterGroups = useMemo(() => Array.from(new Set(timetables.map((item) => item.semester))).sort().reverse(), [timetables])

  const run = async (action: () => Promise<void>, fallback: string) => {
    setPending(true); setError(null)
    try { await action() }
    catch (caught) { setError(caught instanceof Error ? caught.message : fallback) }
    finally { setPending(false) }
  }

  const saveProfile = () => run(async () => {
    const updated = await updateCurrentUser({ name: name.trim(), grade, department })
    setUser(updated); onUserChange(updated)
    if (department) {
      const profile = { schemaVersion: 2 as const, department, currentGrade: grade as 1 | 2 | 3 | 4, academicBasis: null, updatedAt: new Date().toISOString() }
      saveAcademicProfile(profile)
    }
    onMessage('계정정보를 저장했습니다.')
  }, '계정정보를 저장하지 못했습니다.')

  const saveCurrent = () => run(async () => {
    await createSavedTimetable(timetableName.trim() || '내 시간표', currentDraft)
    await refresh(); onMessage('현재 시간표를 저장했습니다.')
  }, '시간표를 저장하지 못했습니다.')

  const resetCourseForm = () => { setEditingCourseId(null); setCourseName(''); setCredits(3); setCategory('전공'); setArea(''); setSemester(''); setCourseStatus('COMPLETED') }
  const saveCourse = () => run(async () => {
    const values = { courseName: courseName.trim(), credits, category: category.trim(), area: area.trim() || null, semester: semester.trim() || null, status: courseStatus }
    if (editingCourseId) await updateCompletedCourse(editingCourseId, values)
    else await createCompletedCourse(values)
    resetCourseForm(); await refresh(); onMessage('이수과목을 저장했습니다.')
  }, '이수과목을 저장하지 못했습니다.')

  const startEditCourse = (item: CompletedCourse) => {
    setEditingCourseId(item.id); setCourseName(item.courseName); setCredits(item.credits); setCategory(item.category); setArea(item.area ?? ''); setSemester(item.semester ?? ''); setCourseStatus(item.status)
  }

  const logout = () => run(async () => { await logoutAuthSession(); onUserChange(null); onMessage('로그아웃되었습니다.'); onBack() }, '로그아웃하지 못했습니다.')
  const removeAccount = () => run(async () => { await deleteCurrentUser(deleteConfirmation); onUserChange(null); localStorage.removeItem('pl-timetabler:profile:v2'); onMessage('회원 탈퇴가 완료되었습니다.'); onBack() }, '회원 탈퇴를 처리하지 못했습니다.')

  return <main className="my-page">
    <header className="page-header"><button type="button" className="text-button" onClick={onBack}>← 시간표로</button><div><h1>마이페이지</h1><p>{user?.studentNumber ?? '계정'}의 저장된 정보를 관리합니다.</p></div></header>
    {error && <div className="global-error" role="alert"><span>{error}</span><button type="button" onClick={() => refresh()}>다시 시도</button></div>}

    <section className="mypage-section" aria-labelledby="account-heading"><div className="section-heading"><div><h2 id="account-heading">계정정보</h2><p>학번은 학교 이메일 계정과 연결되어 변경할 수 없습니다.</p></div></div><div className="mypage-form-grid">
      <label><span>학번</span><input value={user?.studentNumber ?? ''} disabled /></label>
      <label><span>이름</span><input value={name} maxLength={120} onChange={(event) => setName(event.target.value)} /></label>
      <label><span>학년</span><select value={grade} onChange={(event) => setGrade(Number(event.target.value))}>{[1, 2, 3, 4].map((value) => <option value={value} key={value}>{value}학년</option>)}</select></label>
      <label><span>학과</span><select value={department} onChange={(event) => setDepartment(event.target.value)}><option value="">선택</option>{departments.map((item) => <option value={item.academicUnit} key={item.academicUnit}>{item.academicUnit}</option>)}</select></label>
    </div><button type="button" className="primary-button" disabled={pending || !name.trim() || !department} onClick={saveProfile}>계정정보 저장</button></section>

    <section className="mypage-section" aria-labelledby="consent-heading"><div className="section-heading"><div><h2 id="consent-heading">개인정보 동의</h2><p>동의 내역은 버전별로 보관합니다.</p></div></div>
      <label className="check-row"><input type="checkbox" checked={consentChecked} onChange={(event) => setConsentChecked(event.target.checked)} /><span><strong>개인정보 수집·이용에 동의합니다.</strong><small>계정정보, 시간표, 리뷰와 이수내역 저장에 사용합니다.</small></span></label>
      <button type="button" className="secondary-button" disabled={pending || !consentChecked} onClick={() => run(async () => { await createPrivacyConsent(); setConsentChecked(false); await refresh() }, '동의를 저장하지 못했습니다.')}>동의 저장</button>
      <ul className="simple-list">{consents.map((item) => <li key={item.id}><span>{item.consentVersion}</span><small>{new Date(item.agreedAt).toLocaleString('ko-KR')}</small></li>)}</ul>
    </section>

    <section className="mypage-section" aria-labelledby="timetable-heading"><div className="section-heading"><div><h2 id="timetable-heading">저장한 시간표</h2><p>여러 시간표를 저장하고 비교하거나 이전 학기 기록을 확인합니다.</p></div><label className="inline-check"><input type="checkbox" checked={favoriteOnly} onChange={(event) => setFavoriteOnly(event.target.checked)} />즐겨찾기만</label></div>
      <div className="inline-create"><input aria-label="저장할 시간표 이름" value={timetableName} onChange={(event) => setTimetableName(event.target.value)} /><button type="button" className="primary-button" disabled={pending} onClick={saveCurrent}>현재 시간표 저장</button></div>
      {semesterGroups.length > 0 && <p className="mypage-meta">저장된 학기: {semesterGroups.join(', ')}</p>}
      <div className="saved-card-list">{visibleTimetables.map((item) => <article key={item.id}><div><input aria-label={`${item.name} 이름`} value={names[item.id] ?? item.name} onChange={(event) => setNames((current) => ({ ...current, [item.id]: event.target.value }))} /><small>{item.semester} · {new Date(item.updatedAt).toLocaleDateString('ko-KR')}</small></div><div className="card-actions">
        <button type="button" onClick={() => onLoadTimetable({ schemaVersion: 1, semester: item.semester, dataVersion: item.dataVersion, items: item.items, preferences: item.preferences, updatedAt: item.updatedAt })}>불러오기</button>
        <button type="button" onClick={() => run(async () => { await updateSavedTimetable(item.id, { name: names[item.id] }); await refresh() }, '이름을 변경하지 못했습니다.')}>이름 저장</button>
        {item.semester === currentDraft.semester && <button type="button" onClick={() => run(async () => { await updateSavedTimetableSections(item.id, currentDraft); await updateSavedTimetable(item.id, { preferences: currentDraft.preferences }); await refresh(); onMessage('현재 편집 내용을 저장한 시간표에 반영했습니다.') }, '시간표를 수정하지 못했습니다.')}>현재 내용으로 수정</button>}
        <button type="button" onClick={() => run(async () => { await setSavedTimetableFavorite(item.id, !item.favorite); await refresh() }, '즐겨찾기를 변경하지 못했습니다.')}>{item.favorite ? '★ 해제' : '☆ 즐겨찾기'}</button>
        <button type="button" onClick={() => run(async () => { await copySavedTimetable(item.id); await refresh() }, '복사하지 못했습니다.')}>복사</button>
        <button type="button" onClick={() => run(async () => { const share = await createTimetableShare(item.id); await navigator.clipboard.writeText(share.shareUrl); onMessage('공유 링크를 복사했습니다.') }, '공유 링크를 만들지 못했습니다.')}>공유</button>
        <button type="button" onClick={() => run(async () => { const result = await importTimetableCourses(item.id); await refresh(); onMessage(`${result.importedCourses.length}과목을 수강 중으로 등록했습니다.`) }, '시간표 과목을 등록하지 못했습니다.')}>수강 중 등록</button>
        <button type="button" className="danger-text" onClick={() => run(async () => { await deleteSavedTimetable(item.id); await refresh() }, '시간표를 삭제하지 못했습니다.')}>삭제</button>
      </div></article>)}</div>
    </section>

    <section className="mypage-section" aria-labelledby="completed-heading"><div className="section-heading"><div><h2 id="completed-heading">이수과목</h2><p>완료 과목 기준 총 {summary.totalCredits}학점 · 전공 {summary.majorCredits} · 교양 {summary.liberalCredits}</p></div></div>
      <div className="completed-form"><label><span>과목명</span><input value={courseName} onChange={(event) => setCourseName(event.target.value)} /></label><label><span>학점</span><input type="number" min="0.5" max="30" step="0.5" value={credits} onChange={(event) => setCredits(Number(event.target.value))} /></label><label><span>이수구분</span><input value={category} onChange={(event) => setCategory(event.target.value)} /></label><label><span>교양 영역</span><input value={area} onChange={(event) => setArea(event.target.value)} placeholder="해당하는 경우" /></label><label><span>학기</span><input value={semester} onChange={(event) => setSemester(event.target.value)} placeholder="2026-1" /></label><label><span>상태</span><select value={courseStatus} onChange={(event) => setCourseStatus(event.target.value as CompletedCourseStatus)}><option value="IN_PROGRESS">수강 중</option><option value="COMPLETED">이수 완료</option></select></label></div>
      <div className="form-actions">{editingCourseId && <button type="button" className="text-button" onClick={resetCourseForm}>수정 취소</button>}<button type="button" className="primary-button" disabled={pending || !courseName.trim() || !category.trim()} onClick={saveCourse}>{editingCourseId ? '이수과목 수정' : '이수과목 추가'}</button></div>
      <div className="saved-card-list">{completed.map((item) => <article key={item.id}><div><strong>{item.courseName}</strong><small>{item.credits}학점 · {item.category}{item.area ? ` · ${item.area}` : ''} · {item.status === 'COMPLETED' ? '이수 완료' : '수강 중'}</small></div><div className="card-actions"><button type="button" onClick={() => startEditCourse(item)}>수정</button>{item.status === 'IN_PROGRESS' && <button type="button" onClick={() => run(async () => { await updateCompletedCourse(item.id, { status: 'COMPLETED' }); await refresh() }, '상태를 변경하지 못했습니다.')}>이수 완료</button>}<button type="button" className="danger-text" onClick={() => run(async () => { await deleteCompletedCourse(item.id); await refresh() }, '이수과목을 삭제하지 못했습니다.')}>삭제</button></div></article>)}</div>
    </section>

    <section className="mypage-section" aria-labelledby="reviews-heading"><div className="section-heading"><div><h2 id="reviews-heading">내 리뷰</h2><p>작성한 리뷰 {reviews.length}개</p></div></div><div className="saved-card-list">{reviews.map((item) => <article key={item.id}><div><strong>{item.courseName} · ★ {item.rating}</strong><p>{item.content}</p><small>{item.professor ?? '교수 미정'} · {item.semester}</small></div><button type="button" className="danger-text" onClick={() => run(async () => { await deleteCourseReview(item.id); await refresh() }, '리뷰를 삭제하지 못했습니다.')}>삭제</button></article>)}</div></section>

    <section className="mypage-section danger-zone" aria-labelledby="account-actions-heading"><h2 id="account-actions-heading">계정 관리</h2><button type="button" className="secondary-button" disabled={pending} onClick={logout}>로그아웃</button><div><label><span>탈퇴하려면 ‘회원탈퇴’를 입력하세요.</span><input value={deleteConfirmation} onChange={(event) => setDeleteConfirmation(event.target.value)} /></label><button type="button" className="danger-button" disabled={pending || deleteConfirmation !== '회원탈퇴'} onClick={removeAccount}>회원 탈퇴</button></div></section>
  </main>
}
