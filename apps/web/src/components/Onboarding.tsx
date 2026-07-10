import { useEffect, useMemo, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'
import { createAcademicProfile } from '../domain/profile'
import type { AcademicProfile, DepartmentSource, EntryType, SectionGroup, StudentClassification } from '../types'

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
  const [step, setStep] = useState<Step>(mode === 'EDIT' ? 'DEPARTMENT' : 'WELCOME')
  const [query, setQuery] = useState('')
  const [department, setDepartment] = useState(initialProfile?.department ?? '')
  const [admissionYear, setAdmissionYear] = useState(initialProfile?.admissionYear ?? 2026)
  const [currentGrade, setCurrentGrade] = useState<1 | 2 | 3 | 4>(initialProfile?.currentGrade ?? 1)
  const [entryType, setEntryType] = useState<EntryType>(initialProfile?.entryType ?? 'FRESHMAN')
  const [studentType, setStudentType] = useState<StudentClassification>(initialProfile?.studentType ?? 'UNKNOWN')
  const [sectionGroup, setSectionGroup] = useState<SectionGroup>(initialProfile?.sectionGroup ?? 'UNKNOWN')
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

  const finish = (group = sectionGroup) => {
    onComplete(createAcademicProfile({ department, admissionYear, currentGrade, entryType, studentType, sectionGroup: group }))
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

  return <dialog ref={dialogRef} className="onboarding" aria-labelledby="onboarding-title" onKeyDown={keepFocusInside} onCancel={(event) => { event.preventDefault(); onSkip() }}>
    <div className="onboarding-frame">
      {step !== 'WELCOME' && <header className="onboarding-header">{step === 'DETAILS' || mode === 'FIRST_RUN' ? <button type="button" className="text-button" onClick={() => setStep(step === 'DETAILS' ? 'DEPARTMENT' : 'WELCOME')}>← 이전</button> : <span aria-hidden="true" />}<span>{step === 'DEPARTMENT' ? '1 / 2' : '2 / 2'}</span><button type="button" className="text-button" onClick={onSkip}>{mode === 'EDIT' ? '닫기' : '건너뛰기'}</button></header>}
      {step === 'WELCOME' && <section className="welcome-step">
        <div className="welcome-brand" aria-hidden="true">PL</div>
        <div><p className="eyebrow">대진대학교 시간표 도우미</p><h1 id="onboarding-title">원하는 시간표를<br />더 쉽게 만들어 보세요</h1><p>학과와 학년을 알려주면 공식 자료로 확인 가능한 필수 과목부터 연결해 드려요. 과목은 확인한 뒤 직접 추가합니다.</p></div>
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
        <div><p className="eyebrow">추천 범위를 정확하게</p><h1 id="onboarding-title">현재 학적 정보를 알려주세요</h1><p>입학연도와 전형에 맞는 범위만 판단하고, 불확실한 요건은 확인 필요로 안내합니다.</p></div>
        <div className="onboarding-fields">
          <label><span>입학연도</span><select value={admissionYear} onChange={(event) => setAdmissionYear(Number(event.target.value))}>{Array.from({ length: 15 }, (_, index) => 2026 - index).map((year) => <option value={year} key={year}>{year}학년도</option>)}</select></label>
          <fieldset><legend>현재 학년</legend><div className="segmented-control">{([1, 2, 3, 4] as const).map((grade) => <button type="button" className={currentGrade === grade ? 'selected' : ''} aria-pressed={currentGrade === grade} key={grade} onClick={() => setCurrentGrade(grade)}>{grade}학년</button>)}</div></fieldset>
          <fieldset><legend>입학 구분</legend><div className="choice-cards"><button type="button" className={entryType === 'FRESHMAN' ? 'selected' : ''} aria-pressed={entryType === 'FRESHMAN'} onClick={() => setEntryType('FRESHMAN')}><strong>신입학</strong><small>입학연도 요건 점검에 사용</small></button><button type="button" className={entryType === 'TRANSFER' ? 'selected' : ''} aria-pressed={entryType === 'TRANSFER'} onClick={() => setEntryType('TRANSFER')}><strong>편입학</strong><small>인정학점은 별도 확인</small></button></div></fieldset>
          <fieldset><legend>학생 구분</legend><div className="segmented-control section-group-control"><button type="button" className={studentType === 'UNKNOWN' ? 'selected' : ''} aria-pressed={studentType === 'UNKNOWN'} onClick={() => setStudentType('UNKNOWN')}>모름</button><button type="button" className={studentType === 'DOMESTIC' ? 'selected' : ''} aria-pressed={studentType === 'DOMESTIC'} onClick={() => setStudentType('DOMESTIC')}>국내학생</button><button type="button" className={studentType === 'INTERNATIONAL' ? 'selected' : ''} aria-pressed={studentType === 'INTERNATIONAL'} onClick={() => setStudentType('INTERNATIONAL')}>외국인·기타</button></div><p className="field-help">국내학생 전용 교양필수를 구분할 때 사용합니다. 모르면 자동 판정하지 않습니다.</p></fieldset>
          <fieldset><legend>학번 끝자리 분반</legend><div className="segmented-control section-group-control"><button type="button" className={sectionGroup === 'UNKNOWN' ? 'selected' : ''} aria-pressed={sectionGroup === 'UNKNOWN'} onClick={() => setSectionGroup('UNKNOWN')}>모름·없음</button><button type="button" className={sectionGroup === 'ODD' ? 'selected' : ''} aria-pressed={sectionGroup === 'ODD'} onClick={() => setSectionGroup('ODD')}>홀수</button><button type="button" className={sectionGroup === 'EVEN' ? 'selected' : ''} aria-pressed={sectionGroup === 'EVEN'} onClick={() => setSectionGroup('EVEN')}>짝수</button></div><p className="field-help">학과에서 홀수·짝수 지정 분반을 안내받은 경우에만 선택하세요. 공식 분반표가 확인된 학과에서만 자동 배치에 적용됩니다.</p></fieldset>
        </div>
        <div className="onboarding-actions"><button type="button" className="primary-button" onClick={() => finish()}>시간표 만들기</button><small>저장한 정보는 이 브라우저에서 언제든 바꿀 수 있어요.</small></div>
      </section>}
    </div>
  </dialog>
}
