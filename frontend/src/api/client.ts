import type { AlertRecord, AssistantResponse, Explanation, GroupAnalytics, PeerComparison, PortfolioAnalytics, PortfolioRiskRow, PriorityRecord, ProjectDetail, ProjectListItem, ScenarioRecommendations, TrajectoryPoint, WhatIfConfig, WhatIfResult } from "../types";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || "/api").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message: string, public status?: number, public endpoint?: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { signal, headers: { Accept: "application/json" } });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    const apiError = new ApiError("PAIMANA API is unavailable. Start the FastAPI backend and try again.", undefined, path);
    if (import.meta.env.DEV) console.error("PAIMANA API request failed", { endpoint: path, status: undefined, detail: apiError.message });
    throw apiError;
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const apiError = new ApiError(body?.detail || `API request failed (${response.status})`, response.status, path);
    if (import.meta.env.DEV) console.error("PAIMANA API request failed", { endpoint: path, status: response.status, detail: apiError.message });
    throw apiError;
  }
  return response.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { method: "POST", headers: { Accept: "application/json", "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!response.ok) { const data = await response.json().catch(() => null); const apiError = new ApiError(data?.detail || `API request failed (${response.status})`, response.status, path); if (import.meta.env.DEV) console.error("PAIMANA API request failed", { endpoint: path, status: response.status, detail: apiError.message }); throw apiError; }
  return response.json() as Promise<T>;
}

function collection<T>(payload: unknown, key: string): T[] {
  if (Array.isArray(payload)) return payload as T[];
  throw new ApiError(`Invalid API response: expected ${key} collection.`);
}

let projectListPromise: Promise<ProjectListItem[]> | null = null;
const detailCache = new Map<string, Promise<ProjectDetail>>();
const trajectoryCache = new Map<string, Promise<TrajectoryPoint[]>>();
const explanationCache = new Map<string, Promise<Explanation>>();

export function getProjects(signal?: AbortSignal) {
  if (signal) return request<ProjectListItem[]>("/projects", signal);
  projectListPromise ??= request<ProjectListItem[]>("/projects").catch((error) => {
    projectListPromise = null;
    throw error;
  });
  return projectListPromise;
}

export function getProject(projectId: string, signal?: AbortSignal) {
  if (signal) return request<ProjectDetail>(`/projects/${encodeURIComponent(projectId)}`, signal);
  if (!detailCache.has(projectId)) detailCache.set(projectId, request(`/projects/${encodeURIComponent(projectId)}`));
  return detailCache.get(projectId)!;
}

export function getTrajectory(projectId: string, signal?: AbortSignal) {
  if (signal) return request<TrajectoryPoint[]>(`/projects/${encodeURIComponent(projectId)}/trajectory`, signal);
  if (!trajectoryCache.has(projectId)) trajectoryCache.set(projectId, request(`/projects/${encodeURIComponent(projectId)}/trajectory`));
  return trajectoryCache.get(projectId)!;
}

export function getExplanation(projectId: string, signal?: AbortSignal) {
  if (signal) return request<Explanation>(`/projects/${encodeURIComponent(projectId)}/explanation`, signal);
  if (!explanationCache.has(projectId)) explanationCache.set(projectId, request(`/projects/${encodeURIComponent(projectId)}/explanation`));
  return explanationCache.get(projectId)!;
}

let portfolioPromise: Promise<PortfolioRiskRow[]> | null = null;
export function hydratePortfolioRisk(projects: ProjectListItem[], onProgress?: (done: number, total: number, rows: PortfolioRiskRow[]) => void) {
  if (portfolioPromise) return portfolioPromise;
  portfolioPromise = (async () => {
    if (projects.every((item) => item.risk_level && item.data_reliability_score != null)) {
      const rows = projects.map((item) => ({ ...item, risk_level: item.risk_level!, latest_quality_score: item.data_reliability_score!, risk_change: item.risk_change_1m ?? null }));
      onProgress?.(rows.length, rows.length, rows);
      return rows;
    }
    const output: PortfolioRiskRow[] = [];
    let cursor = 0;
    const workers = Array.from({ length: Math.min(16, projects.length) }, async () => {
      while (cursor < projects.length) {
        const index = cursor++;
        const project = projects[index];
        try {
          const trajectory = await getTrajectory(project.canonical_project_id);
          const latest = trajectory.at(-1);
          const previous = trajectory.at(-2);
          if (latest) {
            output.push({
              ...project,
              risk_level: latest.risk_level,
              latest_quality_score: latest.data_quality_score,
              risk_change: previous ? latest.predicted_delay_probability_3m - previous.predicted_delay_probability_3m : null,
            });
          }
        } catch {
          // A single project failure should not hide the rest of the portfolio.
        }
        if (onProgress && (output.length % 20 === 0 || cursor >= projects.length)) onProgress(Math.min(cursor, projects.length), projects.length, [...output]);
      }
    });
    await Promise.all(workers);
    return output;
  })().catch((error) => {
    portfolioPromise = null;
    throw error;
  });
  return portfolioPromise;
}

export const getPeers = (id: string) => request<PeerComparison>(`/projects/${encodeURIComponent(id)}/peers`);
export const getAlerts = (limit = 500) => request<unknown>(`/alerts?limit=${limit}`).then(payload => collection<AlertRecord>(payload, "alerts"));
export const getProjectAlerts = (id: string) => request<unknown>(`/projects/${encodeURIComponent(id)}/alerts`).then(payload => collection<AlertRecord>(payload, "alerts"));
export const getWhatIfConfig = (id: string) => request<WhatIfConfig>(`/projects/${encodeURIComponent(id)}/what-if/config`);
export const runWhatIf = (id: string, values: Record<string, number>) => post<WhatIfResult>(`/projects/${encodeURIComponent(id)}/what-if`, { changes: values });
export const getScenarios = (id: string) => request<ScenarioRecommendations>(`/projects/${encodeURIComponent(id)}/scenarios`);
export const getPortfolioAnalytics = () => request<PortfolioAnalytics>("/analytics/portfolio");
export const getSectorAnalytics = () => request<unknown>("/analytics/sectors").then(payload => collection<GroupAnalytics>(payload, "sectors"));
export const getMinistryAnalytics = () => request<unknown>("/analytics/ministries").then(payload => collection<GroupAnalytics>(payload, "ministries"));
export const getStateAnalytics = () => request<unknown>("/analytics/states").then(payload => collection<GroupAnalytics>(payload, "states"));
export const askAssistant = (question: string, projectId?: string) => post<AssistantResponse>("/assistant/query", { question, ...(projectId ? { project_id: projectId } : {}) });
export const getPriorities = (limit = 2804) => request<PriorityRecord[]>(`/priorities?limit=${limit}`);
export const getProjectPriority = (id: string) => request<PriorityRecord>(`/projects/${encodeURIComponent(id)}/priority`);

export const api = { getProjects, getProject, getTrajectory, getExplanation, hydratePortfolioRisk, getPeers, getAlerts, getProjectAlerts, getWhatIfConfig, runWhatIf, getScenarios, getPortfolioAnalytics, getSectorAnalytics, getMinistryAnalytics, getStateAnalytics, askAssistant, getPriorities, getProjectPriority };
