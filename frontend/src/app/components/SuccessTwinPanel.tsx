import { useState } from 'react';
import type {
  Crisis,
  TwinResult,
  MemoResponse,
  AftershockResult,
  VectorNeighbor,
  ProjectListItem,
} from '../../lib/api';
import { explainCrisis, getVectorNeighbors } from '../../lib/api';

interface SuccessTwinPanelProps {
  crises: Crisis[];
  epicenter: string;
  simulationResult: AftershockResult | null;
  projects: ProjectListItem[];
  twinResult: TwinResult | null;
  twinLoading: boolean;
  twinError: string | null;
  onFindTwin: () => void;
  memoResult: MemoResponse | null;
  memoLoading: boolean;
  memoError: string | null;
  onGenerateMemo: () => void;
  canGenerateMemo: boolean;
}

function formatDisplaced(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

function formatCostUsd(n: number): string {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(1)}K`;
  return `$${n.toLocaleString()}`;
}

/** Normalize severity to 0–10 so crises are comparable. Uses min–max over the full crisis set. */
function normalizeSeverityTo10(severity: number, allCrises: Crisis[]): number {
  const values = allCrises.map((c) => c.severity).filter((s): s is number => typeof s === 'number');
  if (values.length === 0) return Math.max(0, Math.min(10, severity * 2)); // fallback: assume 0–5 scale → *2
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (max <= min) return 5;
  return Math.max(0, Math.min(10, (10 * (severity - min)) / (max - min)));
}

/**
 * Diminishing returns: each extra % of funding change has a smaller effect on coverage.
 * effective_delta = sign(δ) × (1 − e^{-|δ|}), so e.g. +10% → ~9.5%, +50% → ~39%, +100% → ~63%.
 */
function effectiveFundingImpact(deltaFundingPct: number): number {
  if (deltaFundingPct === 0) return 0;
  const abs = Math.abs(deltaFundingPct);
  const effective = (1 - Math.exp(-abs)) * (deltaFundingPct > 0 ? 1 : -1);
  return effective;
}

/**
 * Time horizon effect on coverage: over time, underfunded situations tend to worsen (gap widens),
 * well-funded ones can settle (coverage drifts up). horizonSteps = 1 or 2 (years proxy from run).
 */
function timeHorizonCoverageDrift(coverageAfterFunding: number, horizonSteps: number): number {
  if (horizonSteps <= 0) return 0;
  const years = horizonSteps;
  if (coverageAfterFunding < 0.5) {
    return -0.04 * years * (0.5 - coverageAfterFunding);
  }
  return 0.02 * years * coverageAfterFunding;
}

/** Coverage = share of assessed need that is funded. Can exceed 1 (overfunded). Uses diminishing returns for funding change; optional time-horizon effect (worsens if underfunded, settles if well-funded). */
function coverageFromCrisis(
  fundingReceived: number,
  fundingRequired: number,
  deltaFundingPct: number | null,
  horizonSteps: number | null = null
): number | null {
  if (fundingRequired <= 0) return null;
  const baseline = fundingReceived / fundingRequired;
  const afterFunding =
    deltaFundingPct == null ? baseline : baseline * (1 + effectiveFundingImpact(deltaFundingPct));
  const afterFundingClamped = Math.max(0, afterFunding);
  if (horizonSteps == null || horizonSteps <= 0) return afterFundingClamped;
  const drift = timeHorizonCoverageDrift(afterFundingClamped, horizonSteps);
  return Math.max(0, Math.min(2, afterFundingClamped + drift));
}

export function SuccessTwinPanel({
  crises,
  epicenter,
  simulationResult,
  projects,
  twinResult,
  twinLoading,
  twinError,
  onFindTwin,
  memoResult,
  memoLoading,
  memoError,
  onGenerateMemo,
  canGenerateMemo,
}: SuccessTwinPanelProps) {
  const [activeTab, setActiveTab] = useState<'impact' | 'ai'>('impact');
  const [explanation, setExplanation] = useState('');
  const [explLoading, setExplLoading] = useState(false);
  const [neighbors, setNeighbors] = useState<VectorNeighbor[] | null>(null);
  const [neighborsLoading, setNeighborsLoading] = useState(false);

  const handleCountryClick = (iso: string) => {
    window.dispatchEvent(new CustomEvent('FOCUS_MAP_COUNTRY', { detail: iso }));
  };

  const handleAskWhy = async () => {
    if (!simulationResult) return;
    setExplLoading(true);
    setExplanation('');
    const epicenterCrisis = crises.find(
      (c) =>
        c.country === simulationResult.epicenter ||
        c.id.toUpperCase().startsWith(simulationResult.epicenter)
    );
    const crisisPayload: Record<string, string | number> = {
      country: simulationResult.epicenter,
      year: simulationResult.baseline_year,
    };
    if (epicenterCrisis) {
      const epAffected = simulationResult.affected?.find(
        (a) => (a.country || '').toUpperCase() === (simulationResult.epicenter || '').toUpperCase()
      );
      const baselineSev = typeof epicenterCrisis.severity === 'number' ? epicenterCrisis.severity : 0;
      const dSev = epAffected?.delta_severity ?? 0;
      const severityNorm = crises.length > 0 ? normalizeSeverityTo10(baselineSev + dSev, crises) : baselineSev + dSev;
      const covRatio = coverageFromCrisis(
        epicenterCrisis.funding_received ?? 0,
        epicenterCrisis.funding_required ?? 0,
        simulationResult.delta_funding_pct ?? null,
        simulationResult.horizon_steps ?? null
      );
      const covPct = covRatio != null ? Math.round(covRatio * 100) : null;
      crisisPayload.severity_score = severityNorm / 10;
      crisisPayload.coverage_pct = covPct ?? 0;
      crisisPayload.funding_gap_usd = Math.max(
        0,
        (epicenterCrisis.funding_required ?? 0) - (epicenterCrisis.funding_received ?? 0)
      );
      crisisPayload.underfunded_status =
        covPct == null ? '—' : covPct < 50 ? 'Underfunded vs peers' : covPct >= 100 ? 'Overfunded' : 'Adequately funded';
    }
    try {
      const res = await explainCrisis({
        query:
          'Explain why this crisis might be overlooked and why the funding change leads to this spillover—cause and effect, not just the numbers.',
        context: {
          crisis: crisisPayload,
          aftershock_totals: simulationResult.totals
            ? {
                total_delta_displaced: simulationResult.totals.total_delta_displaced,
                total_extra_cost_usd: simulationResult.totals.total_extra_cost_usd,
              }
            : {},
        },
      });
      setExplanation(res.answer);
    } catch {
      setExplanation('Explanation unavailable.');
    } finally {
      setExplLoading(false);
    }
  };

  const referenceProjectId = twinResult?.target_project_id ?? null;
  const handleFetchNeighbors = async () => {
    if (!referenceProjectId) return;
    setNeighborsLoading(true);
    setNeighbors(null);
    try {
      const res = await getVectorNeighbors(referenceProjectId);
      setNeighbors(res.neighbors || []);
    } catch {
      setNeighbors([]);
    } finally {
      setNeighborsLoading(false);
    }
  };

  const affectedSorted = simulationResult?.affected
    ? [...simulationResult.affected].sort((a, b) => (b.delta_displaced ?? 0) - (a.delta_displaced ?? 0))
    : [];

  const effectiveEpicenter = simulationResult?.epicenter ?? epicenter;
  const epicenterCrisisForLookup = effectiveEpicenter
    ? crises.find(
        (c) =>
          c.country === effectiveEpicenter ||
          c.id.toUpperCase().startsWith(effectiveEpicenter)
      )
    : null;

  // Spillover metrics: comparable framework (normalized severity 0–10, coverage = share funded)
  const epicenterCrisis = simulationResult ? epicenterCrisisForLookup : null;
  const epicenterAffected = simulationResult?.affected?.find(
    (a) => (a.country || '').toUpperCase() === (simulationResult?.epicenter || '').toUpperCase()
  );
  const baselineSeverity = epicenterCrisis != null && typeof epicenterCrisis.severity === 'number' ? epicenterCrisis.severity : null;
  const deltaSeverity = epicenterAffected?.delta_severity ?? 0;

  // Severity: normalized 0–10 across all crises so we can compare one crisis to another
  const severityRawForNorm =
    baselineSeverity != null ? baselineSeverity + deltaSeverity : null;
  const severityOutOf10 =
    severityRawForNorm != null && crises.length > 0
      ? normalizeSeverityTo10(severityRawForNorm, crises).toFixed(1)
      : null;

  // Coverage: share funded; scenario = funding change (diminishing returns) + time-horizon effect (worsens if underfunded, settles if well-funded)
  const coverageRatio =
    epicenterCrisis != null &&
    typeof epicenterCrisis.funding_received === 'number' &&
    typeof epicenterCrisis.funding_required === 'number'
      ? coverageFromCrisis(
          epicenterCrisis.funding_received,
          epicenterCrisis.funding_required,
          simulationResult?.delta_funding_pct ?? null,
          simulationResult?.horizon_steps ?? null
        )
      : null;
  const coveragePct = coverageRatio != null ? Math.round(coverageRatio * 100) : null;
  const underfundedStatus =
    coveragePct != null
      ? coveragePct < 50
        ? 'Underfunded vs peers'
        : coveragePct >= 100
          ? 'Overfunded'
          : 'Adequately funded'
      : null;

  return (
    <div className="flex flex-col h-full bg-[#0f1421]">
      <div className="flex border-b border-gray-800 shrink-0 px-2 pt-2">
        <button
          onClick={() => setActiveTab('impact')}
          className={`px-4 py-3 text-sm font-medium transition-colors border-b-2 ${
            activeTab === 'impact' ? 'border-teal-500 text-teal-400' : 'border-transparent text-gray-500 hover:text-gray-300'
          }`}
        >
          Spillover Metrics
        </button>
        <button
          onClick={() => setActiveTab('ai')}
          className={`px-4 py-3 text-sm font-medium transition-colors border-b-2 ${
            activeTab === 'ai' ? 'border-teal-500 text-teal-400' : 'border-transparent text-gray-500 hover:text-gray-300'
          }`}
        >
          Success Twin & Memo
        </button>
      </div>

      <div className="p-6 overflow-y-auto flex-1">
        {activeTab === 'impact' && (
          <div className="space-y-6">
            <section>
              <h3 className="text-xs uppercase tracking-wider text-gray-500 mb-4">Affected Countries</h3>
              {affectedSorted.length === 0 ? (
                <p className="text-sm text-gray-500">Run a scenario to see spillover impacts.</p>
              ) : (
                <div className="space-y-3">
                  {affectedSorted.map((c, idx) => (
                    <div
                      key={c.country}
                      onClick={() => handleCountryClick(c.country)}
                      className="bg-[#1a1f2e] border border-gray-800 rounded p-3 cursor-pointer hover:border-gray-500 transition-colors"
                    >
                      <div className="flex justify-between items-center mb-1">
                        <span className="font-medium text-gray-200">{idx + 1}. {c.country}</span>
                        <span className="text-red-400 text-sm font-mono">+{formatDisplaced(c.delta_displaced ?? 0)} displaced</span>
                      </div>
                      <div className="text-xs text-amber-400 font-mono">+{formatCostUsd(c.extra_cost_usd ?? 0)} response cost</div>
                    </div>
                  ))}
                </div>
              )}
            </section>

            {/* Spillover Metrics: scenario-adjusted by funding change and time horizon */}
            <section className="mt-6">
              <h3 className="text-xs uppercase tracking-wider text-gray-500 mb-2">Spillover Metrics</h3>
              <div className="flex flex-wrap gap-2 mb-3 justify-center">
                <span className="inline-flex items-center px-3 py-1.5 rounded-md bg-[#1a1f2e] border border-gray-700 text-sm text-gray-300">
                  Severity: <span className="font-mono text-teal-400 ml-1">{severityOutOf10 ?? '—'} {severityOutOf10 != null ? '/ 10' : ''}</span>
                </span>
                <span className="inline-flex items-center px-3 py-1.5 rounded-md bg-[#1a1f2e] border border-gray-700 text-sm text-gray-300">
                  Coverage: <span className="font-mono text-teal-400 ml-1">{coveragePct != null ? `${coveragePct}% funded` : '—'}</span>
                </span>
                <span className="inline-flex items-center px-3 py-1.5 rounded-md bg-[#1a1f2e] border border-gray-700 text-sm text-gray-300">
                  Status: <span className="text-amber-400 ml-1">{underfundedStatus ?? '—'}</span>
                </span>
              </div>
              <div className="text-[11px] text-gray-500 border border-gray-800 rounded-md bg-[#0a0e1a] p-3 space-y-3">
                <div>
                  <div className="font-medium text-gray-400 mb-1.5">Definitions (what we mean)</div>
                  <p><span className="text-teal-500/90">Severity:</span> Relative intensity of the crisis (scale of need, displacement risk, etc.). Higher = worse. Normalized to 0–10 across the set for comparability. <strong>Time horizon</strong> affects it via the simulation: longer horizon = more propagation of stress (can get worse in surrounding areas).</p>
                  <p><span className="text-teal-500/90">Coverage:</span> For this situation, the share of assessed need that is funded: <code className="text-gray-500">funding_received ÷ funding_required</code>. 100% = need fully met; &gt;100% = overfunded; &lt;100% = gap. <strong>Time horizon</strong> adds a drift: underfunded situations tend to worsen over time; well-funded ones can settle.</p>
                  <p><span className="text-teal-500/90">Status:</span> Label from Coverage only: &lt;50% = Underfunded vs peers; 50–99% = Adequately funded; ≥100% = Overfunded.</p>
                </div>
                <div>
                  <div className="font-medium text-gray-400 mb-1.5">How we calculate them</div>
                  <p><span className="text-teal-500/90">Severity:</span> Crisis baseline + simulation <code className="text-gray-500">delta_severity</code> (stress propagates over <strong>time horizon</strong>—longer horizon = more steps = more spillover), then min–max normalized to 0–10.</p>
                  <p><span className="text-teal-500/90">Coverage:</span> <code className="text-gray-500">funding_received / funding_required</code>; after a run, effective funding change (diminishing returns) plus a <strong>time-horizon effect</strong>: if underfunded (&lt;50%), coverage drifts down over time; if well-funded, it can settle (drift up). Can exceed 100%.</p>
                  <p><span className="text-teal-500/90">Status:</span> From Coverage only, using the thresholds above.</p>
                </div>
              </div>
            </section>

            <section className="mt-8 bg-[#0a0e1a] border border-gray-800 rounded-lg p-4">
              <h3 className="text-xs uppercase tracking-wider text-teal-600 mb-2">Ask Sphinx why</h3>
              <button
                onClick={handleAskWhy}
                disabled={!simulationResult || explLoading}
                className="text-teal-400 hover:text-teal-300 text-sm font-medium transition-colors disabled:opacity-50"
              >
                {explLoading ? 'Asking…' : 'Ask Sphinx why'}
              </button>
              {explanation && <p className="text-sm text-gray-400 leading-relaxed mt-3">{explanation}</p>}
            </section>
          </div>
        )}

        {activeTab === 'ai' && (
          <div className="space-y-8">
            <section>
              <h3 className="text-xs uppercase tracking-wider text-gray-500 mb-4">Success Twin</h3>
              <div className="bg-[#1a1f2e] border border-gray-800 rounded-lg p-4 space-y-3">
                <p className="text-xs text-gray-500">
                  Matches the selected crisis (epicenter) and finds a similar project <span className="text-teal-400 font-medium">within that country</span>.
                </p>
                {epicenter && (
                  <p className="text-sm text-gray-300">
                    Crisis: <span className="text-teal-400">{epicenter}</span>
                  </p>
                )}
                <button
                  onClick={onFindTwin}
                  disabled={twinLoading || !epicenter}
                  className="text-teal-400 hover:text-teal-300 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {twinLoading ? 'Searching...' : 'Find Success Twin ↗'}
                </button>
                {twinResult && (
                  <div className="pt-3 border-t border-gray-800 text-sm text-gray-300 space-y-2">
                    <div>
                      <span className="text-gray-500">Twin: </span>
                      <span className="font-medium text-teal-400">{twinResult.twin_name ?? twinResult.twin_project_id}</span>
                      <span className="text-gray-500 ml-1">({twinResult.twin_project_id})</span>
                    </div>
                    {twinResult.bullets?.length > 0 && (
                      <ul className="list-disc list-inside text-gray-400 text-xs space-y-1">
                        {twinResult.bullets.map((b, i) => (
                          <li key={i}>{b}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </div>
            </section>

            <section>
              <h3 className="text-xs uppercase tracking-wider text-gray-500 mb-4">Similar projects (VectorAI)</h3>
              <div className="bg-[#1a1f2e] border border-gray-800 rounded-lg p-4">
                <p className="text-xs text-gray-500 mb-2">
                  {referenceProjectId ? (
                    <>
                      Similar to{' '}
                      <span className="text-teal-400">
                        {projects.find((p) => p.id === referenceProjectId)?.name ?? referenceProjectId}
                      </span>
                      <span className="text-gray-500 ml-1">({referenceProjectId})</span>
                    </>
                  ) : (
                    'Find Success Twin first to enable similar projects (uses crisis-matched reference).'
                  )}
                </p>
                <p className="text-xs text-gray-500 mb-3">
                  Use these to compare sector, funding levels, and delivery models in similar contexts.
                </p>
                <button
                  onClick={handleFetchNeighbors}
                  disabled={neighborsLoading || !referenceProjectId}
                  className="text-teal-400 hover:text-teal-300 text-sm font-medium transition-colors disabled:opacity-50"
                >
                  {neighborsLoading ? 'Loading…' : 'Find similar projects'}
                </button>
                {neighbors !== null && (neighbors.length === 0 ? (
                  <p className="text-sm text-gray-500 mt-3">No similar projects available yet.</p>
                ) : (
                  <ul className="mt-4 space-y-4 text-sm text-gray-300">
                    {neighbors?.map((n, idx) => {
                      const id = n.project_id ?? n.id ?? '—';
                      const name = n.name ?? id;
                      const meta = [n.country, n.sector ?? n.cluster].filter(Boolean).join(' · ');
                      const ratioPct = typeof n.ratio === 'number' ? `${Math.round(n.ratio * 100)}% funded` : '';
                      const simPct = typeof n.similarity_score === 'number' ? `${(n.similarity_score * 100).toFixed(0)}% similar` : '';
                      const titleParts = [meta, ratioPct, simPct].filter(Boolean).join(' · ');
                      const bullets = n.insight_bullets ?? [];
                      return (
                        <li key={String(id) + idx} className="border border-gray-800 rounded p-3 bg-[#0f1421]">
                          <div className="font-medium text-teal-400">{name}</div>
                          {titleParts && <div className="text-xs text-gray-500 mt-0.5">{titleParts}</div>}
                          {bullets.length > 0 && (
                            <ul className="mt-2 list-disc list-inside text-xs text-gray-400 space-y-0.5">
                              {bullets.map((b, i) => (
                                <li key={i}>{b}</li>
                              ))}
                            </ul>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                ))}
              </div>
            </section>

            <section>
              <h3 className="text-xs uppercase tracking-wider text-gray-500 mb-4">Contrarian Decision Memo</h3>
              <div className="bg-[#1a1f2e] border border-gray-800 rounded-lg p-4 flex flex-col h-[250px]">
                <div className="flex-1 overflow-y-auto mb-4 text-sm text-gray-400">
                  {memoLoading ? <p className="animate-pulse">Analyzing risk factors...</p> : memoResult ? <p>{memoResult.body}</p> : <p>Run a scenario first.</p>}
                </div>
                <button onClick={onGenerateMemo} disabled={!canGenerateMemo || memoLoading} className="w-full bg-teal-900/50 hover:bg-teal-900 text-teal-400 border border-teal-800 py-2 rounded text-sm transition-colors disabled:opacity-50">
                  Generate Memo
                </button>
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}