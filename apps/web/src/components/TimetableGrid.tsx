import type { CSSProperties } from "react";

import type { Section, Session } from "../api/client";
import { formatMinute } from "../domain/timetable";

const DAYS: Session["day"][] = ["월", "화", "수", "목", "금"];
const START_MINUTE = 9 * 60;
const END_MINUTE = 22 * 60;
const HOURS = Array.from({ length: 14 }, (_, index) => 9 + index);

interface TimetableGridProps {
  sections: readonly Section[];
  conflictingIds: ReadonlySet<string>;
}

function courseColor(courseCode: string): number {
  return [...courseCode].reduce((value, character) => value + character.charCodeAt(0), 0) % 6;
}

export function TimetableGrid({ sections, conflictingIds }: TimetableGridProps) {
  return (
    <section className="timetable-section" aria-labelledby="timetable-heading">
      <div className="section-heading-row">
        <h1 id="timetable-heading">내 시간표</h1>
        <span className="section-count">{sections.length}개 분반</span>
      </div>
      <div className="timetable-grid" aria-hidden="true">
        <div className="grid-corner" />
        {DAYS.map((day) => (
          <div className="day-heading" key={day}>
            {day}
          </div>
        ))}
        <div className="time-axis">
          {HOURS.map((hour) => (
            <span key={hour} style={{ top: `${((hour * 60 - START_MINUTE) / (END_MINUTE - START_MINUTE)) * 100}%` }}>
              {hour}
            </span>
          ))}
        </div>
        {DAYS.map((day) => (
          <div className="day-column" key={day}>
            {HOURS.slice(0, -1).map((hour) => (
              <span className="hour-line" key={hour} />
            ))}
            {sections.flatMap((section) =>
              section.sessions
                .filter((session) => session.day === day)
                .map((session) => {
                  const top = ((session.startMinute - START_MINUTE) / (END_MINUTE - START_MINUTE)) * 100;
                  const height = ((session.endMinute - session.startMinute) / (END_MINUTE - START_MINUTE)) * 100;
                  const style = { top: `${top}%`, height: `${height}%` } satisfies CSSProperties;
                  return (
                    <div
                      className={`course-block course-color-${courseColor(section.courseCode)}${conflictingIds.has(section.id) ? " is-conflicting" : ""}`}
                      key={`${section.id}-${session.day}-${session.startMinute}`}
                      style={style}
                    >
                      <strong>{section.name}</strong>
                      <span>{section.sectionCode}분반</span>
                    </div>
                  );
                }),
            )}
          </div>
        ))}
      </div>
      <div className="sr-only" aria-label="요일별 시간표 목록">
        {DAYS.map((day) => (
          <section key={day}>
            <h2>{day}요일</h2>
            <ul>
              {sections.flatMap((section) =>
                section.sessions
                  .filter((session) => session.day === day)
                  .map((session) => (
                    <li key={`${section.id}-${session.startMinute}`}>
                      {section.name}, {formatMinute(session.startMinute)}부터 {formatMinute(session.endMinute)}까지
                    </li>
                  )),
              )}
            </ul>
          </section>
        ))}
      </div>
    </section>
  );
}

