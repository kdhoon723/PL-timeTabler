import { useDeferredValue, useEffect, useMemo, useRef, useState } from "react";

import type { Section } from "../api/client";
import { formatSessions } from "../domain/timetable";

interface CourseSearchDialogProps {
  open: boolean;
  sections: readonly Section[];
  selectedIds: ReadonlySet<string>;
  onSelect: (section: Section) => void;
  onClose: () => void;
}

function normalized(value: string): string {
  return value.replaceAll(/\s+/g, "").toLocaleLowerCase("ko-KR");
}

export function CourseSearchDialog({
  open,
  sections,
  selectedIds,
  onSelect,
  onClose,
}: CourseSearchDialogProps) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const deferredQuery = useDeferredValue(query);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return undefined;
    inputRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose, open]);

  const categories = useMemo(
    () => [...new Set(sections.map((section) => section.category))].toSorted(),
    [sections],
  );
  const results = useMemo(() => {
    const needle = normalized(deferredQuery);
    return sections
      .filter((section) => !category || section.category === category)
      .filter((section) => {
        if (!needle) return true;
        return normalized(
          `${section.name} ${section.professor ?? ""} ${section.courseCode} ${section.category}`,
        ).includes(needle);
      })
      .slice(0, 80);
  }, [category, deferredQuery, sections]);

  if (!open) return null;
  return (
    <div className="sheet-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="search-sheet" role="dialog" aria-modal="true" aria-labelledby="search-title">
        <header className="sheet-header">
          <div>
            <h2 id="search-title">과목 추가</h2>
            <p>과목명·교수명·과목코드로 찾을 수 있습니다.</p>
          </div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="과목 검색 닫기">
            닫기
          </button>
        </header>
        <div className="search-controls">
          <label>
            <span>과목 검색</span>
            <input
              ref={inputRef}
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="예: 컴퓨팅사고, 김선경, 922601"
            />
          </label>
          <label>
            <span>이수구분</span>
            <select value={category} onChange={(event) => setCategory(event.target.value)}>
              <option value="">전체</option>
              {categories.map((item) => (
                <option key={item}>{item}</option>
              ))}
            </select>
          </label>
        </div>
        <p className="result-count" aria-live="polite">
          {results.length}개 분반 표시
        </p>
        <ul className="course-results">
          {results.map((section) => (
            <li key={section.id}>
              <div>
                <strong>{section.name}</strong>
                <span>
                  {section.courseCode} · {section.sectionCode}분반 · {section.professor ?? "담당교수 미정"}
                </span>
                <span>{formatSessions(section)} · {section.credits}학점</span>
              </div>
              <button
                className={selectedIds.has(section.id) ? "secondary-button" : "primary-button"}
                type="button"
                onClick={() => onSelect(section)}
              >
                {selectedIds.has(section.id) ? "선택됨" : "추가"}
              </button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

