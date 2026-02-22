import { useRef, useEffect, useState } from 'react';
import csvDataUrl from '../../../../dataml/data/raw/misfit_final_analysis.csv';
import type { AftershockResult, AffectedCountryImpact, EpicenterNeighborsResponse } from '../../lib/api';
import { fetchEpicenterNeighbors } from '../../lib/api';

/** Only count nodes with prob_underfunded_next above this threshold. */
const UNDERFUNDED_THRESHOLD = 0.5;

function countUnderfundedCrises(affected: AffectedCountryImpact[]): number {
  return affected.filter(
    (a) => typeof a.prob_underfunded_next === 'number' && a.prob_underfunded_next > UNDERFUNDED_THRESHOLD
  ).length;
}

interface ImpactPanelProps {
  simulationResult: AftershockResult | null;
  epicenter: string;
  simulationLoading: boolean;
  simulationError: string | null;
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

export function ImpactPanel({
  simulationResult,
  epicenter,
  simulationLoading,
  simulationError,
}: ImpactPanelProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const hasScenario = !!simulationResult;
  const [neighborsData, setNeighborsData] = useState<EpicenterNeighborsResponse | null>(null);

  useEffect(() => {
    if (!epicenter) {
      setNeighborsData(null);
      return;
    }
    fetchEpicenterNeighbors(epicenter)
      .then((res) => setNeighborsData(res))
      .catch(() => setNeighborsData(null));
  }, [epicenter]);

  useEffect(() => {
    if (!iframeRef.current) return;
    const epicenterToShow = simulationResult?.epicenter ?? epicenter;
    const affectedToShow = simulationResult?.affected?.map((a) => {
      const sev = a.projected_severity ?? 0.5;
      const cov = a.projected_coverage ?? 0.5;
      const postCriticality = Math.max(0, Math.min(1, (sev + (1 - cov)) / 2));
      return {
        country: a.country,
        delta_displaced: a.delta_displaced ?? 0,
        extra_cost_usd: a.extra_cost_usd ?? 0,
        prob_underfunded_next: a.prob_underfunded_next,
        projected_severity: a.projected_severity,
        projected_coverage: a.projected_coverage,
        post_criticality: postCriticality,
      };
    }) ?? [];
    const neighborsToSend = epicenter && neighborsData ? neighborsData.neighbors : [];
    const epicenterCriticality = epicenter && neighborsData ? neighborsData.epicenter_criticality : undefined;
    iframeRef.current.contentWindow?.postMessage({
      type: 'AFTERSHOCK_AFFECTED',
      epicenter: epicenterToShow,
      epicenter_criticality: epicenterCriticality,
      affected: affectedToShow,
      neighbors: neighborsToSend,
    }, '*');
  }, [epicenter, neighborsData, simulationResult?.epicenter, simulationResult?.affected]);

  useEffect(() => {
    const handleFocus = (e: Event) => {
      const customEvent = e as CustomEvent;
      if (iframeRef.current) {
        iframeRef.current.contentWindow?.postMessage(
          { type: 'FOCUS_COUNTRY', iso: customEvent.detail },
          '*'
        );
      }
    };
    window.addEventListener('FOCUS_MAP_COUNTRY', handleFocus);
    return () => window.removeEventListener('FOCUS_MAP_COUNTRY', handleFocus);
  }, []);

  return (
    <div className="p-6">
      <div className="bg-[#0f1421] border border-gray-800 rounded-lg mb-6 h-[400px] relative overflow-hidden">
        <iframe
          ref={iframeRef}
          src={`/map_test.html?data=${encodeURIComponent(csvDataUrl)}`}
          title="Fragility & Funding Map"
          className="absolute top-0 left-0 w-full h-full border-none"
        />
      </div>

      {simulationError ? (
        <div className="mb-6 py-3 px-4 bg-red-950/30 border border-red-800 rounded-lg">
          <p className="text-sm text-red-400">{simulationError}</p>
          <p className="text-xs text-gray-500 mt-1">Try a different epicenter or funding level.</p>
        </div>
      ) : !hasScenario && !simulationLoading ? (
        <div className="mb-6 p-6 bg-[#0f1421] border border-gray-800 rounded-lg text-center">
          <p className="text-sm text-gray-500">Run a scenario to see impact.</p>
          <p className="text-xs text-gray-600 mt-2">Adjust funding and click Run Aftershock.</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-[#0f1421] border border-gray-800 rounded-lg p-4 border-t-2 border-t-red-500">
              <div className="text-xs text-gray-500 mb-2 uppercase tracking-wider">Extra displaced (region)</div>
              <div className="text-2xl text-red-400 font-mono">
                {simulationLoading ? '...' : `+${formatDisplaced(simulationResult?.totals.total_delta_displaced ?? 0)}`}
              </div>
              <div className="text-xs text-gray-600 mt-1">
                across {simulationResult?.totals.affected_countries ?? 0} neighboring countries
              </div>
            </div>

            <div className="bg-[#0f1421] border border-gray-800 rounded-lg p-4 border-t-2 border-t-amber-500">
              <div className="text-xs text-gray-500 mb-2 uppercase tracking-wider">Extra response cost</div>
              <div className="text-2xl text-amber-400 font-mono">
                {simulationLoading ? '...' : `+${formatCostUsd(simulationResult?.totals.total_extra_cost_usd ?? 0)}`}
              </div>
              <div className="text-xs text-gray-600 mt-1">projected additional funding needed</div>
            </div>

            <div className="bg-[#0f1421] border border-gray-800 rounded-lg p-4 border-t-2 border-t-teal-500">
              <div className="text-xs text-gray-500 mb-2 uppercase tracking-wider">New underfunded crises</div>
              <div className="text-2xl text-gray-100 font-mono">
                {simulationLoading
                  ? '...'
                  : simulationResult
                    ? `+${countUnderfundedCrises(simulationResult.affected)}`
                    : '0'}
              </div>
              <div className="text-xs text-gray-600 mt-1">countries crossing underfunded threshold</div>
              <p className="text-[10px] text-gray-600 mt-0.5">
                Threshold: P(underfunded next year) &gt; {UNDERFUNDED_THRESHOLD}
              </p>
            </div>
          </div>

          <section className="mt-6">
            <h3 className="text-xs uppercase tracking-wider text-gray-500 mb-4">Affected Countries</h3>
            {simulationLoading ? (
              <p className="text-sm text-gray-500">Loading...</p>
            ) : !simulationResult?.affected?.length ? (
              <p className="text-sm text-gray-500">Run a scenario to see spillover impacts.</p>
            ) : (
              <div className="space-y-3">
                {[...simulationResult.affected]
                  .sort((a, b) => (b.delta_displaced ?? 0) - (a.delta_displaced ?? 0))
                  .map((c, idx) => (
                    <div
                      key={c.country}
                      onClick={() => window.dispatchEvent(new CustomEvent('FOCUS_MAP_COUNTRY', { detail: c.country }))}
                      className="bg-[#1a1f2e] border border-gray-800 rounded p-3 cursor-pointer hover:border-gray-500 transition-colors"
                    >
                      <div className="flex justify-between items-center mb-1">
                        <span className="font-medium text-gray-200">
                          {idx + 1}. {c.country}
                        </span>
                        <span className="text-red-400 text-sm font-mono">
                          +{formatDisplaced(c.delta_displaced ?? 0)} displaced
                        </span>
                      </div>
                      <div className="text-xs text-amber-400 font-mono">
                        +{formatCostUsd(c.extra_cost_usd ?? 0)} response cost
                      </div>
                    </div>
                  ))}
              </div>
            )}
          </section>

          {simulationResult?.totals && (
            <section className="mt-6 bg-[#0a0e1a] border border-gray-800 rounded-lg p-4">
              <h3 className="text-xs uppercase tracking-wider text-teal-600 mb-2">AI Summary</h3>
              <p className="text-sm text-gray-400 leading-relaxed">
                {simulationResult.delta_funding_pct < 0
                  ? `Cutting ${Math.round(-simulationResult.delta_funding_pct * 100)}% from ${simulationResult.epicenter}'s crisis is projected to add ${formatDisplaced(simulationResult.totals.total_delta_displaced)} displaced and ${formatCostUsd(simulationResult.totals.total_extra_cost_usd)} in extra response costs.`
                  : `Increasing funding by ${Math.round(simulationResult.delta_funding_pct * 100)}% for ${simulationResult.epicenter} may reduce spillover; current projection: ${formatDisplaced(simulationResult.totals.total_delta_displaced)} displaced, ${formatCostUsd(simulationResult.totals.total_extra_cost_usd)} response cost.`}
              </p>
            </section>
          )}
        </>
      )}
    </div>
  );
}
