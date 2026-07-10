import { useCallback, useEffect, useState } from "react";

import type { Section } from "../api/client";
import { loadDraft, saveDraft } from "../domain/storage";
import { createDraft, type DraftTimetable } from "../domain/timetable";

interface HistoryState {
  past: DraftTimetable[];
  present: DraftTimetable;
  future: DraftTimetable[];
}

export function useTimetable(semester: string, sectionsById: ReadonlyMap<string, Section>) {
  const [history, setHistory] = useState<HistoryState>(() => ({
    past: [],
    present: loadDraft(semester),
    future: [],
  }));

  useEffect(() => {
    setHistory({ past: [], present: loadDraft(semester), future: [] });
  }, [semester]);

  useEffect(() => {
    saveDraft(history.present);
  }, [history.present]);

  const commit = useCallback((next: DraftTimetable) => {
    setHistory((current) => {
      if (JSON.stringify(current.present) === JSON.stringify(next)) return current;
      return {
        past: [...current.past.slice(-19), current.present],
        present: next,
        future: [],
      };
    });
  }, []);

  const addSection = useCallback(
    (section: Section) => {
      const current = history.present;
      const sameCourse = current.sectionIds.find(
        (id) => sectionsById.get(id)?.courseCode === section.courseCode,
      );
      const nextIds = sameCourse
        ? current.sectionIds.map((id) => (id === sameCourse ? section.id : id))
        : [...current.sectionIds, section.id];
      const nextLocks = current.lockedSectionIds.map((id) =>
        id === sameCourse ? section.id : id,
      );
      commit({ ...current, sectionIds: nextIds, lockedSectionIds: nextLocks });
    },
    [commit, history.present, sectionsById],
  );

  const removeSection = useCallback(
    (sectionId: string) => {
      const current = history.present;
      commit({
        ...current,
        sectionIds: current.sectionIds.filter((id) => id !== sectionId),
        lockedSectionIds: current.lockedSectionIds.filter((id) => id !== sectionId),
      });
    },
    [commit, history.present],
  );

  const toggleLock = useCallback(
    (sectionId: string) => {
      const current = history.present;
      const locked = current.lockedSectionIds.includes(sectionId);
      commit({
        ...current,
        lockedSectionIds: locked
          ? current.lockedSectionIds.filter((id) => id !== sectionId)
          : [...current.lockedSectionIds, sectionId],
      });
    },
    [commit, history.present],
  );

  const applySectionIds = useCallback(
    (sectionIds: readonly string[]) => {
      const validIds = sectionIds.filter((id) => sectionsById.has(id));
      commit({
        ...history.present,
        sectionIds: [...validIds],
        lockedSectionIds: history.present.lockedSectionIds.filter((id) => validIds.includes(id)),
      });
    },
    [commit, history.present, sectionsById],
  );

  const undo = useCallback(() => {
    setHistory((current) => {
      const previous = current.past.at(-1);
      if (!previous) return current;
      return {
        past: current.past.slice(0, -1),
        present: previous,
        future: [current.present, ...current.future],
      };
    });
  }, []);

  const redo = useCallback(() => {
    setHistory((current) => {
      const next = current.future[0];
      if (!next) return current;
      return {
        past: [...current.past, current.present],
        present: next,
        future: current.future.slice(1),
      };
    });
  }, []);

  const reset = useCallback(() => commit(createDraft(semester)), [commit, semester]);

  return {
    draft: history.present,
    selectedSections: history.present.sectionIds
      .map((id) => sectionsById.get(id))
      .filter((section): section is Section => section !== undefined),
    addSection,
    removeSection,
    toggleLock,
    applySectionIds,
    undo,
    redo,
    reset,
    canUndo: history.past.length > 0,
    canRedo: history.future.length > 0,
  };
}

