import type { Section } from "../api/client";
import type { TimetableConflict } from "../domain/timetable";
import { sectionsConflict } from "../domain/timetable";

interface ConflictNoticeProps {
  conflicts: readonly TimetableConflict[];
  selected: readonly Section[];
  catalog: readonly Section[];
  onReplace: (section: Section) => void;
}

export function ConflictNotice({ conflicts, selected, catalog, onReplace }: ConflictNoticeProps) {
  if (conflicts.length === 0) return null;
  const target = conflicts[0]?.right;
  const alternatives = target
    ? catalog
        .filter((section) => section.courseCode === target.courseCode && section.id !== target.id)
        .filter((section) =>
          selected
            .filter((selectedSection) => selectedSection.courseCode !== target.courseCode)
            .every((selectedSection) => sectionsConflict(section, selectedSection) === null),
        )
        .slice(0, 2)
    : [];

  return (
    <section className="conflict-notice" role="alert" aria-labelledby="conflict-heading">
      <h2 id="conflict-heading">수업시간이 겹칩니다</h2>
      {conflicts.map((conflict) => (
        <p key={`${conflict.left.id}-${conflict.right.id}`}>
          {conflict.day}요일에 {conflict.left.name}과(와) {conflict.right.name}이 겹칩니다.
        </p>
      ))}
      {alternatives.length > 0 && (
        <div className="alternative-actions">
          <span>충돌 없는 {target?.name} 분반</span>
          {alternatives.map((section) => (
            <button className="secondary-button" type="button" key={section.id} onClick={() => onReplace(section)}>
              {section.sectionCode}분반으로 변경
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

