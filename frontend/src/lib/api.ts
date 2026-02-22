/**
 * Typed client for AidSight FastAPI backend.
 * Uses VITE_API_BASE_URL, defaulting to http://localhost:8000.
 */

const API_BASE =
  (typeof import.meta !== "undefined" && (import.meta as { env?: Record<string, string> }).env?.VITE_API_BASE_URL) ||
  "http://127.0.0.1:8000";

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
  twin_name?: string;
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
  aftershock?: AftershockResult;
}

// --- Aftershock types (match backend AftershockResult) ---

export interface AftershockRequest {
  epicenter: string; // ISO3 code, e.g. "BFA"
  delta_funding_pct: number; // decimal: -0.2 .. +0.2
  horizon_steps: number; // backend "years" or steps (1-2)
}

export interface AffectedCountryImpact {
  country: string;
  delta_severity: number;
  delta_displaced: number;
  extra_cost_usd: number;
  prob_underfunded_next: number;
  explanation?: string;
  /** Simulation: severity 0–1 for X/10 display. */
  projected_severity?: number;
  /** Simulation: coverage 0–1 (epicenter = baseline + funding change). Single source for Coverage % and Status. */
  projected_coverage?: number;
}

export interface TotalsImpact {
  total_delta_displaced: number;
  total_extra_cost_usd: number;
  affected_countries: number;
  max_delta_severity: number;
}

export interface AftershockResult {
  baseline_year: number;
  epicenter: string;
  delta_funding_pct: number;
  horizon_steps: number;
  affected: AffectedCountryImpact[];
  totals: TotalsImpact;
  graph_edges_used?: unknown[];
  notes: string[];
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

/** User-friendly message when aftershock API fails. */
export const AFTERSHOCK_ERROR_MESSAGE =
  "Aftershock simulation failed. Please try a different scenario.";

/**
 * Parse FastAPI-style error response: { detail: string } or { detail: string[] }.
 * Returns a short user-friendly message or null to fall back to generic.
 */
function parseAftershockErrorResponse(text: string): string | null {
  try {
    const json = JSON.parse(text) as { detail?: string | string[] };
    const d = json?.detail;
    if (typeof d === "string") return d.length > 120 ? null : d;
    if (Array.isArray(d)) return d[0] && typeof d[0] === "string" ? d[0].slice(0, 120) : null;
    return null;
  } catch {
    return null;
  }
}

/**
 * Aftershock spillover simulation. Calls POST /simulate/aftershock.
 */
export async function simulateAftershock(params: {
  epicenter: string;
  delta_funding_pct: number;
  horizon_steps: number;
}): Promise<AftershockResult> {
  console.log("[AidSight] simulateAftershock request:", JSON.stringify(params));
  const url = getUrl("/simulate/aftershock");
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
    cache: "no-store",
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    console.error(`Aftershock API error ${res.status}: ${text}`);
    const parsed = parseAftershockErrorResponse(text);
    throw new Error(parsed ?? AFTERSHOCK_ERROR_MESSAGE);
  }

  const data = await res.json();
  console.log("[AidSight] simulateAftershock response:", {
    epicenter: data.epicenter,
    delta_funding_pct: data.delta_funding_pct,
    horizon_steps: data.horizon_steps,
    total_displaced: data.totals?.total_delta_displaced,
    affected: data.affected?.map((a: { country: string }) => a.country),
  });
  return data as AftershockResult;
}

// --- Explain (Sphinx) ---

export interface ExplainResponse {
  answer: string;
}

export async function explainCrisis(payload: {
  query: string;
  context: { crisis?: Record<string, string | number>; aftershock_totals?: Record<string, number> };
}): Promise<ExplainResponse> {
  const res = await fetch(getUrl("/explain/crisis"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to explain crisis");
  return res.json() as Promise<ExplainResponse>;
}

// --- Vector neighbors (VectorAI) ---

export interface VectorNeighbor {
  project_id?: string;
  id?: string;
  similarity_score?: number;
  country?: string;
  cluster?: string;
  ratio?: number;
  [key: string]: unknown;
}

export interface VectorNeighborsResponse {
  project_id: string;
  neighbors: VectorNeighbor[];
}

export interface ProjectListItem {
  id: string;
  name?: string;
  sector?: string;
  country?: string;
  year?: number;
  region?: string;
  description?: string;
}

/** Response from GET /projects/for_crisis; may be a fallback when no project in selected country/year. */
export interface CrisisProjectResponse extends ProjectListItem {
  fallback?: boolean;
  fallback_reason?: string; // e.g. "same_region", "nearest_year", "no_project_in_country"
  region?: string;
}

export async function fetchProjects(): Promise<ProjectListItem[]> {
  const res = await fetch(getUrl("/projects/"));
  if (!res.ok) throw new Error("Failed to fetch projects");
  return res.json() as Promise<ProjectListItem[]>;
}

/** Project for the selected crisis (epicenter). Uses nearest country/year fallback when no exact match. */
export async function fetchProjectForCrisis(
  country: string,
  year?: number
): Promise<CrisisProjectResponse | null> {
  if (!country?.trim()) return null;
  const params = new URLSearchParams({ country: country.trim().toUpperCase() });
  if (year != null) params.set("year", String(year));
  const res = await fetch(getUrl(`/projects/for_crisis?${params}`));
  if (res.status === 404) return null;
  if (!res.ok) throw new Error("Failed to fetch project for crisis");
  return res.json() as Promise<CrisisProjectResponse>;
}

export async function getVectorNeighbors(projectId: string, topK = 5): Promise<VectorNeighborsResponse> {
  const res = await fetch(getUrl(`/projects/${encodeURIComponent(projectId)}/vector_neighbors?top_k=${topK}`));
  if (!res.ok) throw new Error("Failed to fetch neighbors");
  return res.json() as Promise<VectorNeighborsResponse>;
}
