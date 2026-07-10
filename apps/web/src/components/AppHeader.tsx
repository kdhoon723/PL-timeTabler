import { RedoIcon, ShareIcon, UndoIcon } from './Icons'

interface Props {
  credits: number
  canUndo: boolean
  canRedo: boolean
  onUndo: () => void
  onRedo: () => void
  onShare: () => void
  onNavigate: (path: string) => void
}

export function AppHeader({ credits, canUndo, canRedo, onUndo, onRedo, onShare, onNavigate }: Props) {
  return <header className="app-header">
    <button className="brand-button" type="button" onClick={() => onNavigate('/')} aria-label="시간표 편집기로 이동">
      <span className="brand-mark" aria-hidden="true">PL</span><span>2026-1</span>
    </button>
    <div className="header-summary" aria-label={`현재 ${credits}학점`}>{credits}학점</div>
    <nav className="header-actions" aria-label="편집 도구">
      <button className="icon-button" type="button" onClick={onUndo} disabled={!canUndo} aria-label="실행 취소"><UndoIcon /></button>
      <button className="icon-button" type="button" onClick={onRedo} disabled={!canRedo} aria-label="다시 실행"><RedoIcon /></button>
      <button className="icon-button" type="button" onClick={onShare} aria-label="시간표 공유"><ShareIcon /></button>
      <button className="header-link" type="button" onClick={() => onNavigate('/requirements')}>졸업요건</button>
    </nav>
  </header>
}
