import { useCallback, useEffect, useMemo, useState } from "react";

import { fetchCatalog, fetchSemesters, type CatalogPage, type Section } from "./api/client";
import { AppHeader } from "./components/AppHeader";
import { ConflictNotice } from "./components/ConflictNotice";
import { CourseSearchDialog } from "./components/CourseSearchDialog";
import { OptimizerPanel } from "./components/OptimizerPanel";
import { SelectedCourseList } from "./components/SelectedCourseList";
import { TimetableGrid } from "./components/TimetableGrid";
import { loadCatalogCache, saveCatalogCache } from "./domain/storage";
import { findConflicts, summarizeTimetable } from "./domain/timetable";
import { useTimetable } from "./hooks/useTimetable";

type LoadState = "loading" | "ready" | "cached" | "error";

export default function App() {
  const [catalog, setCatalog] = useState<CatalogPage | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoadState("loading");
    setError(null);
    try {
      const semesters = await fetchSemesters(signal);
      const semester = semesters.find((item) => item.isActive) ?? semesters[0];
      if (!semester) throw new Error("사용 가능한 학기 데이터가 없습니다.");
      const page = await fetchCatalog(semester.id, signal);
      setCatalog(page);
      saveCatalogCache(semester.id, page);
      setLoadState("ready");
    } catch (caught) {
      if (signal?.aborted) return;
      const cached = loadCatalogCache<CatalogPage>("2026-1");
      if (cached) {
        setCatalog(cached);
        setLoadState("cached");
      } else {
        setLoadState("error");
        setError(caught instanceof Error ? caught.message : "과목 데이터를 불러오지 못했습니다.");
      }
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  if (!catalog) {
    return (
      <main className="boot-state">
        {loadState === "loading" ? (
          <p aria-live="polite">2026학년도 1학기 과목을 불러오는 중입니다.</p>
        ) : (
          <>
            <h1>과목 데이터를 불러오지 못했습니다</h1>
            <p>{error}</p>
            <button className="primary-button" type="button" onClick={() => void load()}>
              다시 시도
            </button>
          </>
        )}
      </main>
    );
  }

  return (
    <Editor catalog={catalog} loadState={loadState} onOpenSearch={() => setSearchOpen(true)} searchOpen={searchOpen} onCloseSearch={() => setSearchOpen(false)} />
  );
}

interface EditorProps {
  catalog: CatalogPage;
  loadState: LoadState;
  searchOpen: boolean;
  onOpenSearch: () => void;
  onCloseSearch: () => void;
}

function Editor({ catalog, loadState, searchOpen, onOpenSearch, onCloseSearch }: EditorProps) {
  const sectionsById = useMemo(
    () => new Map(catalog.sections.map((section) => [section.id, section])),
    [catalog.sections],
  );
  const timetable = useTimetable(catalog.semester, sectionsById);
  const conflicts = useMemo(() => findConflicts(timetable.selectedSections), [timetable.selectedSections]);
  const conflictingIds = useMemo(
    () => new Set(conflicts.flatMap((conflict) => [conflict.left.id, conflict.right.id])),
    [conflicts],
  );
  const lockedIds = useMemo(() => new Set(timetable.draft.lockedSectionIds), [timetable.draft.lockedSectionIds]);
  const selectedIds = useMemo(() => new Set(timetable.draft.sectionIds), [timetable.draft.sectionIds]);
  const summary = useMemo(() => summarizeTimetable(timetable.selectedSections), [timetable.selectedSections]);

  const selectSection = (section: Section) => {
    timetable.addSection(section);
    onCloseSearch();
  };

  return (
    <div className="app-shell">
      <AppHeader
        semester={catalog.semester}
        credits={summary.credits}
        canUndo={timetable.canUndo}
        canRedo={timetable.canRedo}
        onUndo={timetable.undo}
        onRedo={timetable.redo}
        onReset={timetable.reset}
      />
      {loadState === "cached" && (
        <div className="offline-banner" role="status">
          네트워크에 연결할 수 없어 마지막으로 받은 과목 데이터를 사용합니다.
        </div>
      )}
      <main className="editor-layout">
        <div className="editor-main">
          <ConflictNotice
            conflicts={conflicts}
            selected={timetable.selectedSections}
            catalog={catalog.sections}
            onReplace={timetable.addSection}
          />
          <TimetableGrid sections={timetable.selectedSections} conflictingIds={conflictingIds} />
          <dl className="timetable-summary" aria-label="시간표 요약">
            <div><dt>등교일</dt><dd>{summary.campusDays}일</dd></div>
            <div><dt>빈 시간</dt><dd>{summary.gapMinutes}분</dd></div>
            <div><dt>총 학점</dt><dd>{summary.credits}학점</dd></div>
          </dl>
        </div>
        <aside className="editor-sidebar">
          <SelectedCourseList
            sections={timetable.selectedSections}
            lockedIds={lockedIds}
            conflictingIds={conflictingIds}
            onToggleLock={timetable.toggleLock}
            onRemove={timetable.removeSection}
          />
          <OptimizerPanel
            semester={catalog.semester}
            datasetVersion={catalog.datasetVersion}
            selected={timetable.selectedSections}
            lockedIds={lockedIds}
            onApply={timetable.applySectionIds}
          />
          <p className="data-evidence">
            과목 데이터 {catalog.preparedAt} 기준 · {catalog.total.toLocaleString("ko-KR")}개 분반
          </p>
        </aside>
      </main>
      <button className="add-course-button" type="button" onClick={onOpenSearch}>
        과목 추가
      </button>
      <CourseSearchDialog
        open={searchOpen}
        sections={catalog.sections}
        selectedIds={selectedIds}
        onSelect={selectSection}
        onClose={onCloseSearch}
      />
    </div>
  );
}

