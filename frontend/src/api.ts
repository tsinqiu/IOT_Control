import type {
  EnergyAssessment,
  OverflowRiskAssessment,
  PumpHealthAssessment,
  SystemSummary,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";
export type TimeRange = "latest" | "24h" | "all";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`API ${response.status}: ${path}`);
  }
  return response.json() as Promise<T>;
}

export function fetchSummary(range: TimeRange = "latest") {
  return getJson<SystemSummary>(`/api/part2/summary?range=${range}`);
}

export function fetchEnergy(range: TimeRange = "latest", limit = 5000) {
  return getJson<EnergyAssessment[]>(`/api/part2/energy?range=${range}&limit=${limit}`);
}

export function fetchPumpHealth(range: TimeRange = "latest", limit = 5000) {
  return getJson<PumpHealthAssessment[]>(`/api/part2/pump-health?range=${range}&limit=${limit}`);
}

export function fetchOverflowRisk(range: TimeRange = "latest", limit = 5000) {
  return getJson<OverflowRiskAssessment[]>(`/api/part2/overflow-risk?range=${range}&limit=${limit}`);
}
