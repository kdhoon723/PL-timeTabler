import { useEffect, useMemo, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'
import { ACTIVE_SEMESTER, ACTIVE_SEMESTER_YEAR, academicProgression, createAcademicProfile, expectedFreshmanGrade, supportsSectionGroup } from '../domain/profile'
import type { AcademicBasis, AcademicProfile, DepartmentSource, EntryType, SectionGroup, StudentClassification } from '../types'

interface Props {
  departments: DepartmentSource[]
  initialProfile: AcademicProfile | null
  mode: 'FIRST_RUN' | 'EDIT'
  authAvailable: boolean
  onComplete: (profile: AcademicProfile) => void
  onSkip: () => void
  onLogin: () => void
}

type Step = 'WELCOME' | 'DEPARTMENT' | 'DETAILS'

export function Onboarding({ departments, initialProfile, mode, authAvailable, onComplete, onSkip, onLogin }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const initialBasis = initialProfile?.academicBasis
  const [step, setStep] = useState<Step>(mode === 'EDIT' ? 'DETAILS' : 'WELCOME')
  const [query, setQuery] = useState('')
  const [department, setDepartment] = useState(initialProfile?.department ?? '')
  const [currentGrade, setCurrentGrade] = useState<1 | 2 | 3 | 4>(initialProfile?.currentGrade ?? 1)
  const [useAcademicBasis, setUseAcademicBasis] = useState(mode === 'EDIT' && !!initialBasis)
  const [admissionYear, setAdmissionYear] = useState(initialBasis?.admissionYear ?? ACTIVE_SEMESTER_YEAR)
  const [entryType, setEntryType] = useState<EntryType>(initialBasis?.entryType ?? 'FRESHMAN')
  const [studentType, setStudentType] = useState<StudentClassification>(initialBasis?.studentType ?? 'UNKNOWN')
  const [sectionGroup, setSectionGroup] = useState<SectionGroup>(initialBasis?.sectionGroup ?? 'UNKNOWN')
  const [gradeMismatchAcknowledged, setGradeMismatchAcknowledged] = useState(initialBasis?.gradeMismatchAcknowledged ?? false)
  const transferSelected = entryType === 'TRANSFER'
  const basisEnabled = mode === 'EDIT' ? useAcademicBasis : transferSelected
  const draftBasis: AcademicBasis | null = basisEnabled ? { admissionYear, entryType, studentType, sectionGroup, gradeMismatchAcknowledged: gradeMismatchAcknowledged || undefined } : null
  const draftProfile: AcademicProfile = { schemaVersion: 2, department, currentGrade, academicBasis: draftBasis, updatedAt: initialProfile?.updatedAt ?? '' }
  const progression = academicProgression(draftProfile)
  const gradeMismatch = progression === 'DELAYED' || progression === 'ACCELERATED'
  const delayedProgression = progression === 'DELAYED'
  const expectedGrade = expectedFreshmanGrade(admissionYear)
  const matchingDepartments = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase('ko')
    return departments.filter((item) => !normalized || `${item.academicUnit} ${item.college}`.toLocaleLowerCase('ko').includes(normalized))
  }, [departments, query])

  useEffect(() => {
    const dialog = dialogRef.current
    if (dialog && !dialog.open) dialog.showModal()
    return () => {
      if (dialog?.open) dialog.close()
    }
  }, [])

  const finish = () => {
    if (delayedProgression && !gradeMismatchAcknowledged) return
    onComplete(createAcademicProfile({ department, currentGrade, academicBasis: draftBasis }))
  }

  const setTransfer = (selected: boolean) => {
    setEntryType(selected ? 'TRANSFER' : 'FRESHMAN')
    setGradeMismatchAcknowledged(false)
  }

  const keepFocusInside = (event: KeyboardEvent<HTMLDialogElement>) => {
    if (event.key !== 'Tab') return
    const focusable = [...event.currentTarget.querySelectorAll<HTMLElement>('button:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])')]
      .filter((element) => element.getClientRects().length > 0)
    const first = focusable[0]
    const last = focusable.at(-1)
    if (!first || !last) return
    if (event.shiftKey && (document.activeElement === first || !event.currentTarget.contains(document.activeElement))) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault()
      first.focus()
    }
  }

  const admissionYearField = <label><span>{transferSelected ? '대진대 편입학년도' : '입학연도'}</span><select value={admissionYear} onChange={(event) => { setAdmissionYear(Number(event.target.value)); setGradeMismatchAcknowledged(false) }}>{Array.from({ length: 15 }, (_, index) => ACTIVE_SEMESTER_YEAR - index).map((year) => <option value={year} key={year}>{year}학년도</option>)}</select><small className="field-help">입학연도별 필수과목 범위를 확인할 때만 사용해요.</small></label>

  const transferField = <div className={`transfer-disclosure ${transferSelected ? 'selected' : ''}`}>
    <label><input type="checkbox" checked={transferSelected} onChange={(event) => setTransfer(event.target.checked)} /><span><strong>혹시 편입생인가요?</strong><small>해당하는 경우에만 선택해 주세요.</small></span></label>
    {transferSelected && <div className="transfer-options"><strong>편입 기준으로 안내할게요</strong><p>인정학점과 대체 이수 과목은 학생마다 달라 필수과목을 임의로 확정하지 않아요. 세부 인정 내역은 졸업요건에서 따로 확인할 수 있어요.</p></div>}
  </div>

  return <dialog ref={dialogRef} className="onboarding" aria-labelledby="onboarding-title" onKeyDown={keepFocusInside} onCancel={(event) => { event.preventDefault(); onSkip() }}>
    <div className="onboarding-frame">
      {step !== 'WELCOME' && <header className="onboarding-header">{step === 'DETAILS' || mode === 'FIRST_RUN' ? <button type="button" className="text-button" onClick={() => setStep(step === 'DETAILS' ? 'DEPARTMENT' : 'WELCOME')}>← 이전</button> : <span aria-hidden="true" />}<span>{step === 'DEPARTMENT' ? '1 / 2' : '2 / 2'}</span><button type="button" className="text-button" onClick={onSkip}>{mode === 'EDIT' ? '닫기' : '건너뛰기'}</button></header>}
      {step === 'WELCOME' && <section className="welcome-step">
        <div className="welcome-brand" aria-hidden="true">PL</div>
        <div><p className="eyebrow">대진대학교 시간표 도우미</p><h1 id="onboarding-title">원하는 시간표를<br />더 쉽게 만들어 보세요</h1><p>학과와 학년을 알려주면 전공 과목부터 빠르게 찾을 수 있어요. 과목은 확인한 뒤 직접 추가합니다.</p></div>
        <div className="onboarding-actions"><button autoFocus type="button" className="primary-button" onClick={() => setStep('DEPARTMENT')}>학과 선택하고 시작</button><button type="button" className="secondary-button" onClick={onSkip}>건너뛰고 바로 만들기</button>{authAvailable && <button type="button" className="text-button login-entry" onClick={onLogin}>학교 이메일로 로그인</button>}<small>로그인하지 않아도 모든 시간표 기능을 사용할 수 있어요.</small></div>
      </section>}
      {step === 'DEPARTMENT' && <section className="onboarding-step">
        <div><p className="eyebrow">내 전공에 맞게</p><h1 id="onboarding-title">학과·전공을 선택해 주세요</h1><p>2026 교육과정편람에 확인된 학과만 안내합니다.</p></div>
        <label className="department-search"><span className="sr-only">학과 검색</span><input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder="학과 이름 검색" /></label>
        <div className="department-options" role="listbox" aria-label="학과·전공">
          {matchingDepartments.map((item) => <button type="button" role="option" aria-selected={department === item.academicUnit} className={department === item.academicUnit ? 'selected' : ''} key={item.academicUnit} onClick={() => { setDepartment(item.academicUnit); setStep('DETAILS') }}><span><strong>{item.academicUnit}</strong><small>{item.college}</small></span><span aria-hidden="true">›</span></button>)}
          {!matchingDepartments.length && <p className="empty-copy">일치하는 학과가 없습니다.</p>}
        </div>
      </section>}
      {step === 'DETAILS' && <section className="onboarding-step details-step">
        <div><p className="eyebrow">이번 학기 기준으로</p><h1 id="onboarding-title">몇 학년 시간표를<br />준비할까요?</h1><p>전공 과목을 학년 수준에 맞게 찾는 데 사용해요. 다른 학년 과목도 언제든 검색할 수 있어요.</p></div>
        <div className="onboarding-fields">
          <fieldset><legend>현재 학년</legend><div className="segmented-control">{([1, 2, 3, 4] as const).map((grade) => <button type="button" className={currentGrade === grade ? 'selected' : ''} aria-pressed={currentGrade === grade} key={grade} onClick={() => { setCurrentGrade(grade); setGradeMismatchAcknowledged(false) }}>{grade}학년</button>)}</div></fieldset>
          {mode === 'FIRST_RUN' ? <>{transferField}{transferSelected && admissionYearField}</> : <div className={`academic-basis-disclosure ${useAcademicBasis ? 'selected' : ''}`}>
            <label><input type="checkbox" checked={useAcademicBasis} onChange={(event) => { setUseAcademicBasis(event.target.checked); setGradeMismatchAcknowledged(false) }} /><span><strong>필수과목 추천을 더 정확히</strong><small>입학연도 기준을 추가하면 확인 가능한 필수과목만 안내해요.</small></span></label>
            {useAcademicBasis && <div className="academic-basis-options">{admissionYearField}{transferField}<fieldset><legend>학생 구분</legend><div className="segmented-control section-group-control"><button type="button" className={studentType === 'UNKNOWN' ? 'selected' : ''} aria-pressed={studentType === 'UNKNOWN'} onClick={() => setStudentType('UNKNOWN')}>모름</button><button type="button" className={studentType === 'DOMESTIC' ? 'selected' : ''} aria-pressed={studentType === 'DOMESTIC'} onClick={() => setStudentType('DOMESTIC')}>국내학생</button><button type="button" className={studentType === 'INTERNATIONAL' ? 'selected' : ''} aria-pressed={studentType === 'INTERNATIONAL'} onClick={() => setStudentType('INTERNATIONAL')}>외국인·기타</button></div><p className="field-help">국내학생 전용 교양필수를 구분할 때 사용해요. 모르면 자동 판정하지 않아요.</p></fieldset>{supportsSectionGroup(department) && <fieldset><legend>학번 끝자리 분반</legend><div className="segmented-control section-group-control"><button type="button" className={sectionGroup === 'UNKNOWN' ? 'selected' : ''} aria-pressed={sectionGroup === 'UNKNOWN'} onClick={() => setSectionGroup('UNKNOWN')}>모름·없음</button><button type="button" className={sectionGroup === 'ODD' ? 'selected' : ''} aria-pressed={sectionGroup === 'ODD'} onClick={() => setSectionGroup('ODD')}>홀수</button><button type="button" className={sectionGroup === 'EVEN' ? 'selected' : ''} aria-pressed={sectionGroup === 'EVEN'} onClick={() => setSectionGroup('EVEN')}>짝수</button></div></fieldset>}</div>}
          </div>}
          {gradeMismatch && <div className="profile-consistency-warning" role="alert"><strong>입학연도와 현재 학년을 확인해 주세요</strong><p>{ACTIVE_SEMESTER.replace('-', '학년도 ')}학기 기준 신입학 {admissionYear}학번은 {expectedGrade ? `보통 ${expectedGrade}학년` : '일반적인 4년 재학 범위를 지난 학번'}입니다.</p>{progression === 'ACCELERATED' ? <p>현재 학년이 일반 예상보다 높아 학과 확인 전에는 필수과목을 자동 판정하지 않습니다. 설정은 저장할 수 있습니다.</p> : <label><input type="checkbox" checked={gradeMismatchAcknowledged} onChange={(event) => setGradeMismatchAcknowledged(event.target.checked)} />휴학·복학 등으로 현재 {currentGrade}학년이 맞습니다.</label>}</div>}
        </div>
        <div className="onboarding-actions"><button type="button" className="primary-button" disabled={delayedProgression && !gradeMismatchAcknowledged} onClick={finish}>{mode === 'EDIT' ? '설정 저장' : `${currentGrade}학년 시간표 만들기`}</button><small>저장한 정보는 이 브라우저에서 언제든 바꿀 수 있어요.</small></div>
      </section>}
    </div>
  </dialog>
}
