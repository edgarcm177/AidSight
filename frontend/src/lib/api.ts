/**
 * Typed client for AidSight FastAPI backend.
 * Uses VITE_API_BASE_URL, defaulting to http://localhost:8000.
 */

const API_BASE =
  (typeof import.meta !== "undefined" && (import.meta as { env?: Record<string, string> }).env?.VITE_API_BASE_URL) ||
  "http://localhost:8000";

function getUrl(path: string): string {
  const base = API_BASE.replace(/\/$/, "");
  return path.startsWith("/") ? `${base}${path}` : `${base}/${path}`;
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) {
    const text = await res.text();
    console.error(`API error ${res.status}: ${text}`);
    throw new Error(`API ${res.status}: ${text.slice(0, 200)}`);
  }
  return res.json() as Promise<T>;
}

// --- Types (mirror backend Pydantic models) ---

export interface Crisis {
  id: string;
  name: string;
  country: string;
  region?: string;
  severity: number;
  people_in_need: number;
  funding_required: number;
  funding_received: number;
  coverage: number;
}

export interface SimulationMetrics {
  baseline_ttc_days: number;
  scenario_ttc_days: number;
  baseline_equity_shift_pct: number;
  scenario_equity_shift_pct: number;
  at_risk_population: number;
}

export interface RegionImpact {
  region: string;
  delta_ttc_days: number;
  funding_gap_usd: number;
}

export interface SimulationResult {
  crisis_id: string;
  metrics: SimulationMetrics;
  impacted_regions: RegionImpact[];
}

export interface TwinResult {
  target_project_id: string;
  twin_project_id: string;
  similarity_score: number;
  bullets: string[];
}

export interface MemoResponse {
  title: string;
  body: string;
  key_risks: string[];
}

export interface ScenarioPayload {
  crisis_id: string;
  funding_changes: { sector: string; delta_usd: number }[];
  shock: { inflation_pct: number; drought: boolean; conflict_intensity: number };
  what_if_text?: string;
}

export interface MemoPayload {
  crisis_id: string;
  simulation: SimulationResult;
  scenario?: ScenarioPayload;
  twin?: TwinResult;
}

// --- API functions ---

export async function fetchCrises(): Promise<Crisis[]> {
  return fetchJson<Crisis[]>(getUrl("/crises/"));
}

export async function simulate(crisisId: string, scenarioPayload: ScenarioPayload): Promise<SimulationResult> {
  return fetchJson<SimulationResult>(getUrl("/simulate/"), {
    method: "POST",
    body: JSON.stringify(scenarioPayload),
  });
}

export async function fetchTwin(projectId: string): Promise<TwinResult> {
  return fetchJson<TwinResult>(getUrl(`/twins/${encodeURIComponent(projectId)}`));
}

export async function createMemo(payload: MemoPayload): Promise<MemoResponse> {
  return fetchJson<MemoResponse>(getUrl("/memos/"), {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
