import { createDraft, type DraftTimetable } from "./timetable";

const DRAFT_KEY = "pl-timetabler:draft:v1";
const CATALOG_PREFIX = "pl-timetabler:catalog:v1:";

function isDraft(value: unknown): value is DraftTimetable {
  if (!value || typeof value !== "object") return false;
  const draft = value as Partial<DraftTimetable>;
  return (
    draft.schemaVersion === 1 &&
    typeof draft.semester === "string" &&
    Array.isArray(draft.sectionIds) &&
    draft.sectionIds.every((item) => typeof item === "string") &&
    Array.isArray(draft.lockedSectionIds) &&
    draft.lockedSectionIds.every((item) => typeof item === "string")
  );
}

export function loadDraft(semester: string): DraftTimetable {
  try {
    const raw = window.localStorage.getItem(DRAFT_KEY);
    if (!raw) return createDraft(semester);
    const parsed: unknown = JSON.parse(raw);
    if (!isDraft(parsed) || parsed.semester !== semester) return createDraft(semester);
    return parsed;
  } catch {
    return createDraft(semester);
  }
}

export function saveDraft(draft: DraftTimetable): void {
  window.localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
}

export function loadCatalogCache<T>(semester: string): T | null {
  try {
    const raw = window.localStorage.getItem(`${CATALOG_PREFIX}${semester}`);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

export function saveCatalogCache<T>(semester: string, catalog: T): void {
  try {
    window.localStorage.setItem(`${CATALOG_PREFIX}${semester}`, JSON.stringify(catalog));
  } catch {
    // Catalog caching is best-effort; editing remains available in the current session.
  }
}

