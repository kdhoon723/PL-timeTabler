import type { components } from "./schema";

export type Semester = components["schemas"]["Semester"];
export type CatalogPage = components["schemas"]["CatalogPage"];
export type Section = components["schemas"]["Section"];
export type Session = components["schemas"]["Session"];
export type OptimizationCreate = components["schemas"]["OptimizationCreate"];
export type OptimizationJob = components["schemas"]["OptimizationJobRead"];
export type OptimizationCandidate = components["schemas"]["OptimizationCandidate"];

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    let detail = `요청을 완료하지 못했습니다. (${response.status})`;
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string") detail = payload.detail;
    } catch {
      // The status code remains the reliable fallback when an upstream proxy returns HTML.
    }
    throw new ApiError(detail, response.status);
  }
  return (await response.json()) as T;
}

export function fetchSemesters(signal?: AbortSignal): Promise<Semester[]> {
  return request<Semester[]>("/semesters", { signal });
}

export function fetchCatalog(semester: string, signal?: AbortSignal): Promise<CatalogPage> {
  return request<CatalogPage>(`/catalog/${encodeURIComponent(semester)}?limit=2000`, { signal });
}

export function createOptimization(input: OptimizationCreate): Promise<OptimizationJob> {
  return request<OptimizationJob>("/optimizations", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function fetchOptimization(jobId: string): Promise<OptimizationJob> {
  return request<OptimizationJob>(`/optimizations/${encodeURIComponent(jobId)}`);
}

export function cancelOptimization(jobId: string): Promise<OptimizationJob> {
  return request<OptimizationJob>(`/optimizations/${encodeURIComponent(jobId)}`, {
    method: "DELETE",
  });
}

