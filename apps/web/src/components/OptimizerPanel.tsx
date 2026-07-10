import { useState } from "react";

import {
  createOptimization,
  fetchOptimization,
  type OptimizationJob,
  type Section,
} from "../api/client";
import { summarizeTimetable } from "../domain/timetable";

const TERMINAL = new Set(["OPTIMAL", "FEASIBLE", "INFEASIBLE", "TIME_LIMIT", "FAILED", "CANCELLED"]);

interface OptimizerPanelProps {
  semester: string;
  datasetVersion: string;
  selected: readonly Section[];
  lockedIds: ReadonlySet<string>;
  onApply: (ids: readonly string[]) => void;
}

function wait(milliseconds: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

export function OptimizerPanel({
  semester,
  datasetVersion,
  selected,
  lockedIds,
  onApply,
}: OptimizerPanelProps) {
  const [job, setJob] = useState<OptimizationJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const summary = summarizeTimetable(selected);

  const generate = async () => {
    if (selected.length === 0) return;
    setSubmitting(true);
    setError(null);
    try {
      const required = selected
        .filter((section) => lockedIds.has(section.id))
        .map((section) => section.courseCode);
      const candidates = selected
        .filter((section) => !lockedIds.has(section.id))
        .map((section) => section.courseCode);
      let current = await createOptimization({
        semester,
        datasetVersion,
        requiredCourseCodes: required,
        candidateCourseCodes: candidates,
        excludedCourseCodes: [],
        lockedSectionIds: [...lockedIds],
        selectedSectionIds: selected.map((section) => section.id),
        minCredits: Math.max(0, summary.credits - 3),
        maxCredits: Math.min(30, summary.credits + 3),
        preferences: {
          preferredDaysOff: [],
          minimizeCampusDays: true,
          minimizeGapMinutes: true,
        },
        candidateCount: 3,
        seed: 0,
        timeLimitSeconds: 3,
      });
      setJob(current);
      for (let attempt = 0; attempt < 20 && !TERMINAL.has(current.status); attempt += 1) {
        await wait(800);
        current = await fetchOptimization(current.id);
        setJob(current);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "자동 생성을 시작하지 못했습니다.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="optimizer-panel" aria-labelledby="optimizer-heading">
      <div className="section-heading-row">
        <div>
          <h2 id="optimizer-heading">현재 과목의 분반 개선</h2>
          <p>잠근 분반은 유지하고 공강일과 빈 시간을 줄인 후보를 만듭니다.</p>
        </div>
        <button
          className="secondary-button"
          type="button"
          disabled={selected.length === 0 || submitting}
          onClick={() => void generate()}
        >
          {submitting ? "후보 생성 중" : "분반 후보 만들기"}
        </button>
      </div>
      {error && <p className="inline-error" role="alert">{error}</p>}
      {job && !TERMINAL.has(job.status) && <p className="job-status" aria-live="polite">작업 상태: {job.status}</p>}
      {job?.result?.reasons.map((reason) => <p className="inline-error" key={reason}>{reason}</p>)}
      {job?.result?.candidates && job.result.candidates.length > 0 && (
        <ol className="candidate-list">
          {job.result.candidates.map((candidate) => (
            <li key={candidate.rank}>
              <div>
                <strong>{candidate.rank}안</strong>
                <span>
                  {candidate.metrics.totalCredits}학점 · 등교 {candidate.metrics.campusDays}일 · 빈 시간 {candidate.metrics.gapMinutes}분
                </span>
                {candidate.explanation.map((line) => <span key={line}>{line}</span>)}
              </div>
              <button className="primary-button" type="button" onClick={() => onApply(candidate.sectionIds)}>
                이 후보 적용
              </button>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

