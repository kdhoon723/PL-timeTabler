import type { Section, Session } from "../api/client";

export interface DraftTimetable {
  schemaVersion: 1;
  semester: string;
  sectionIds: string[];
  lockedSectionIds: string[];
}

export interface TimetableConflict {
  left: Section;
  right: Section;
  day: Session["day"];
}

export interface TimetableSummary {
  credits: number;
  campusDays: number;
  gapMinutes: number;
}

export function createDraft(semester: string): DraftTimetable {
  return {
    schemaVersion: 1,
    semester,
    sectionIds: [],
    lockedSectionIds: [],
  };
}

export function sessionsOverlap(left: Session, right: Session): boolean {
  return (
    left.day === right.day &&
    left.startMinute < right.endMinute &&
    right.startMinute < left.endMinute
  );
}

export function sectionsConflict(left: Section, right: Section): Session["day"] | null {
  for (const leftSession of left.sessions) {
    if (right.sessions.some((rightSession) => sessionsOverlap(leftSession, rightSession))) {
      return leftSession.day;
    }
  }
  return null;
}

export function findConflicts(sections: readonly Section[]): TimetableConflict[] {
  const conflicts: TimetableConflict[] = [];
  for (let leftIndex = 0; leftIndex < sections.length; leftIndex += 1) {
    const left = sections[leftIndex];
    if (!left) continue;
    for (let rightIndex = leftIndex + 1; rightIndex < sections.length; rightIndex += 1) {
      const right = sections[rightIndex];
      if (!right) continue;
      const day = sectionsConflict(left, right);
      if (day) conflicts.push({ left, right, day });
    }
  }
  return conflicts;
}

export function summarizeTimetable(sections: readonly Section[]): TimetableSummary {
  const byDay = new Map<Session["day"], Session[]>();
  for (const section of sections) {
    for (const session of section.sessions) {
      const sessions = byDay.get(session.day) ?? [];
      sessions.push(session);
      byDay.set(session.day, sessions);
    }
  }

  let gapMinutes = 0;
  for (const sessions of byDay.values()) {
    const sorted = sessions.toSorted((left, right) => left.startMinute - right.startMinute);
    for (let index = 1; index < sorted.length; index += 1) {
      const previous = sorted[index - 1];
      const current = sorted[index];
      if (previous && current) gapMinutes += Math.max(0, current.startMinute - previous.endMinute);
    }
  }
  return {
    credits: sections.reduce((total, section) => total + section.credits, 0),
    campusDays: byDay.size,
    gapMinutes,
  };
}

export function formatMinute(minute: number): string {
  const hour = Math.floor(minute / 60);
  const remainder = minute % 60;
  return `${hour.toString().padStart(2, "0")}:${remainder.toString().padStart(2, "0")}`;
}

export function formatSessions(section: Section): string {
  if (section.timeToBeAnnounced) return "시간 미정";
  return section.sessions
    .map(
      (session) =>
        `${session.day} ${formatMinute(session.startMinute)}–${formatMinute(session.endMinute)}`,
    )
    .join(", ");
}

