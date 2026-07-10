import { useEffect, useRef, useState } from 'react'
import { RedoIcon, ShareIcon, UndoIcon } from './Icons'
import type { AcademicProfile, AuthSession } from '../types'

interface Props {
  credits: number
  profile: AcademicProfile | null
  authSession: AuthSession
  canUndo: boolean
  canRedo: boolean
  onUndo: () => void
  onRedo: () => void
  onShare: () => void
  onExportPng: () => void
  onExportPdf: () => void
  onNavigate: (path: string) => void
  onProfile: () => void
  onAccount: () => void
}

export function AppHeader({ credits, profile, authSession, canUndo, canRedo, onUndo, onRedo, onShare, onExportPng, onExportPdf, onNavigate, onProfile, onAccount }: Props) {
  const [menuOpen, setMenuOpen] = useState(false)
  const menuButtonRef = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    if (!menuOpen) return
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      setMenuOpen(false)
      menuButtonRef.current?.focus()
    }
    document.addEventListener('keydown', closeOnEscape)
    return () => document.removeEventListener('keydown', closeOnEscape)
  }, [menuOpen])
  const run = (action: () => void) => () => { setMenuOpen(false); action() }

  return <header className="app-header">
    <button className="brand-button" type="button" onClick={() => onNavigate('/')} aria-label="시간표 편집기로 이동">
      <span className="brand-mark" aria-hidden="true">PL</span><span>2026-1</span>
    </button>
    <div className="header-summary" aria-label={`현재 ${credits}학점`}>{credits}학점</div>
    <nav className="header-actions desktop-header-actions" aria-label="편집 도구">
      <button className="profile-chip" type="button" onClick={onProfile} title={profile?.department ?? '학과 설정'}>{profile ? `${profile.department} ${profile.currentGrade}학년` : '학과 설정'}</button>
      <button className="icon-button" type="button" onClick={onUndo} disabled={!canUndo} aria-label="실행 취소"><UndoIcon /></button>
      <button className="icon-button" type="button" onClick={onRedo} disabled={!canRedo} aria-label="다시 실행"><RedoIcon /></button>
      <button className="icon-button" type="button" onClick={onShare} aria-label="시간표 공유"><ShareIcon /></button>
      <button className="header-link" type="button" onClick={() => onNavigate('/requirements')}>졸업요건</button>
      {authSession.available && <button className={`account-button ${authSession.authenticated ? 'authenticated' : ''}`} type="button" onClick={onAccount}>{authSession.authenticated ? '인증됨' : '로그인'}</button>}
    </nav>
    <div className="mobile-command-menu">
      <button ref={menuButtonRef} className="more-button" type="button" aria-haspopup="menu" aria-expanded={menuOpen} aria-controls="mobile-command-list" onClick={() => setMenuOpen((value) => !value)}>더보기</button>
      {menuOpen && <div className="command-menu" id="mobile-command-list" role="menu" aria-label="시간표 명령">
        <button type="button" role="menuitem" onClick={run(onUndo)} disabled={!canUndo}>실행 취소</button>
        <button type="button" role="menuitem" onClick={run(onRedo)} disabled={!canRedo}>다시 실행</button>
        <button type="button" role="menuitem" onClick={run(onShare)}>시간표 공유</button>
        <button type="button" role="menuitem" onClick={run(() => onNavigate('/requirements'))}>졸업요건</button>
        <button type="button" role="menuitem" onClick={run(onExportPng)}>PNG 저장</button>
        <button type="button" role="menuitem" onClick={run(onExportPdf)}>PDF 저장</button>
        <button type="button" role="menuitem" onClick={run(onProfile)}>{profile ? '학적 정보 변경' : '학과 설정'}</button>
        {authSession.available && <button type="button" role="menuitem" onClick={run(onAccount)}>{authSession.authenticated ? '계정 확인' : '로그인'}</button>}
      </div>}
    </div>
  </header>
}
