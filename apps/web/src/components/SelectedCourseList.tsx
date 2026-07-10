import type { Section } from "../api/client";
import { formatSessions } from "../domain/timetable";

interface SelectedCourseListProps {
  sections: readonly Section[];
  lockedIds: ReadonlySet<string>;
  conflictingIds: ReadonlySet<string>;
  onToggleLock: (id: string) => void;
  onRemove: (id: string) => void;
}

export function SelectedCourseList({
  sections,
  lockedIds,
  conflictingIds,
  onToggleLock,
  onRemove,
}: SelectedCourseListProps) {
  return (
    <section className="selected-panel" aria-labelledby="selected-heading">
      <div className="section-heading-row">
        <h2 id="selected-heading">선택 과목</h2>
        <span>{sections.length}개</span>
      </div>
      {sections.length === 0 ? (
        <p className="empty-copy">과목을 추가하면 분반과 충돌 상태를 여기서 확인할 수 있습니다.</p>
      ) : (
        <ul className="selected-list">
          {sections.map((section) => (
            <li className={conflictingIds.has(section.id) ? "has-conflict" : ""} key={section.id}>
              <div>
                <strong>{section.name}</strong>
                <span>
                  {section.sectionCode}분반 · {section.professor ?? "교수 미정"}
                </span>
                <span>{formatSessions(section)}</span>
                {section.timeToBeAnnounced && <span className="status-label warning">시간 미정</span>}
                {conflictingIds.has(section.id) && <span className="status-label danger">충돌</span>}
              </div>
              <div className="row-actions">
                <button
                  className="secondary-button"
                  type="button"
                  aria-pressed={lockedIds.has(section.id)}
                  onClick={() => onToggleLock(section.id)}
                >
                  {lockedIds.has(section.id) ? "잠금 해제" : "잠금"}
                </button>
                <button className="ghost-button danger-text" type="button" onClick={() => onRemove(section.id)}>
                  삭제
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

