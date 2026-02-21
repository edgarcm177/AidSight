const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetchApi<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}

export const api = {
  health: () => fetchApi<{ status: string }>('/health'),
  regions: (preset?: string) =>
    fetchApi<RegionMetric[]>(
      preset ? `/regions?scenario_preset=${preset}` : '/regions'
    ),
  region: (id: string) =>
    fetchApi<{ region: RegionMetric; projects: Project[] }>(`/regions/${id}`),
  runScenario: (params: ScenarioParams) =>
    fetchApi<ScenarioResult>('/scenario/run', {
      method: 'POST',
      body: JSON.stringify(params),
    }),
  projects: (params?: { region_id?: string; flagged?: boolean }) => {
    const q = new URLSearchParams();
    if (params?.region_id) q.set('region_id', params.region_id);
    if (params?.flagged !== undefined) q.set('flagged', String(params.flagged));
    const qs = q.toString();
    return fetchApi<Project[]>(`/projects${qs ? `?${qs}` : ''}`);
  },
  project: (id: string) => fetchApi<Project>(`/projects/${id}`),
  comparables: (id: string, topK = 5) =>
    fetchApi<ComparableTrade[]>(`/projects/${id}/comparables?top_k=${topK}`, {
      method: 'POST',
    }).catch(() => []),
  generateMemo: (context: MemoContext) =>
    fetchApi<Memo>(`/memo/generate`, {
      method: 'POST',
      body: JSON.stringify(context),
    }),
};

export interface RegionMetric {
  region_id: string;
  region_name: string;
  risk_score: number;
  coverage_pct: number;
  funding_gap: number;
  volatility: number;
  runway_months: number;
  coverage_pct_baseline?: number;
  coverage_pct_stressed?: number;
  runway_months_baseline?: number;
  runway_months_stressed?: number;
  required_funding?: number;
  funding_received?: number;
}

export interface ScenarioParams {
  inflation_shock: number;
  climate_shock: number;
  access_shock: number;
  funding_delta: number;
}

export interface ScenarioResult {
  updated_region_metrics: RegionMetric[];
  top_downside_regions: string[];
  suggested_allocations: { region_id: string; delta_funding: number }[];
  regret_score: number;
}

export interface Project {
  project_id: string;
  title: string;
  description: string;
  region_id: string;
  sector: string;
  budget: number;
  beneficiaries: number;
  cost_per_beneficiary?: number;
  flagged?: boolean;
}

export interface ComparableTrade {
  project_id: string;
  title: string;
  similarity: number;
  key_reasons: string[];
  peer_metrics_summary?: Record<string, unknown>;
}

export interface Memo {
  sections: Record<string, string>;
}

export interface MemoContext {
  scenario_params?: ScenarioParams | Record<string, unknown>;
  project?: Project | Record<string, unknown>;
  comparables?: ComparableTrade[] | Record<string, unknown>[];
  region_metrics?: Record<string, unknown>[];
}
