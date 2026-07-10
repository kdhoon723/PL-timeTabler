interface AppHeaderProps {
  semester: string;
  credits: number;
  canUndo: boolean;
  canRedo: boolean;
  onUndo: () => void;
  onRedo: () => void;
  onReset: () => void;
}

export function AppHeader({
  semester,
  credits,
  canUndo,
  canRedo,
  onUndo,
  onRedo,
  onReset,
}: AppHeaderProps) {
  return (
    <header className="app-header">
      <div>
        <span className="sr-only">학기</span>
        <strong>{semester.replace("-", "학년도 ")}학기</strong>
        <span className="credit-summary">{credits}학점</span>
      </div>
      <div className="header-actions" aria-label="편집 기록">
        <button className="icon-button" type="button" onClick={onUndo} disabled={!canUndo}>
          실행 취소
        </button>
        <button className="icon-button" type="button" onClick={onRedo} disabled={!canRedo}>
          다시 실행
        </button>
        <button className="ghost-button" type="button" onClick={onReset}>
          초기화
        </button>
      </div>
    </header>
  );
}

