import { useRef, useEffect } from 'react';
// @ts-ignore
import csvDataUrl from '../../../../dataml/data/raw/misfit_final_analysis.csv';
import type { Crisis, AftershockResult, AffectedCountryImpact } from '../../lib/api';

/** Only count nodes with prob_underfunded_next above this threshold. */
const UNDERFUNDED_THRESHOLD = 0.5;

function countUnderfundedCrises(affected: AffectedCountryImpact[]): number {
  return affected.filter(
    (a) => typeof a.prob_underfunded_next === "number" && a.prob_underfunded_next > UNDERFUNDED_THRESHOLD
  ).length;
}

interface ImpactPanelProps {
  selectedCrisis: Crisis | undefined;
  simulationResult: AftershockResult | null;
  simulationLoading: boolean;
  simulationError: string | null;
  epicenter: string;
  timeHorizon: number;
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
  selectedCrisis,
  simulationResult,
  simulationLoading,
  simulationError,
  epicenter,
  timeHorizon,
}: ImpactPanelProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const hasScenario = !!simulationResult;

  // Handles the Run Aftershock animation
  useEffect(() => {
    if (simulationLoading && iframeRef.current) {
      iframeRef.current.contentWindow?.postMessage({
        type: 'RUN_SHOCKWAVE',
        epicenter: epicenter
      }, '*');
    }
  }, [simulationLoading, epicenter]);

  // Pass aftershock affected data to map for impact visualization
  useEffect(() => {
    if (simulationResult?.affected && iframeRef.current) {
      iframeRef.current.contentWindow?.postMessage({
        type: 'AFTERSHOCK_AFFECTED',
        epicenter: simulationResult.epicenter,
        affected: simulationResult.affected.map((a) => ({
          country: a.country,
          impact: a.delta_displaced, // use delta_displaced as impact score
        })),
      }, '*');
    }
  }, [simulationResult?.epicenter, simulationResult?.affected]);

  // NEW: Listens for clicks from the Right Sidebar list!
  useEffect(() => {
    const handleFocus = (e: Event) => {
      const customEvent = e as CustomEvent;
      if (iframeRef.current) {
        iframeRef.current.contentWindow?.postMessage({
          type: 'FOCUS_COUNTRY',
          iso: customEvent.detail
        }, '*');
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
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-[#0f1421] border border-gray-800 rounded-lg p-4 border-t-2 border-t-red-500">
          <div className="text-xs text-gray-500 mb-2 uppercase tracking-wider">Extra displaced (region)</div>
          <div className="text-2xl text-red-400 font-mono">
            {simulationLoading ? '...' : `+${formatDisplaced(simulationResult?.totals.total_delta_displaced ?? 0)}`}
          </div>
          <div className="text-xs text-gray-600 mt-1">
            across {simulationResult?.totals.affected_countries ?? 0} neighboring countries at T+{timeHorizon}m
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
            {simulationLoading ? '...' : (
              simulationResult
                ? `+${countUnderfundedCrises(simulationResult.affected)}`
                : '0'
            )}
          </div>
          <div className="text-xs text-gray-600 mt-1">countries crossing underfunded threshold</div>
          <p className="text-[10px] text-gray-600 mt-0.5">Threshold: P(underfunded next year) &gt; {UNDERFUNDED_THRESHOLD}</p>
        </div>
      </div>
      )}
    </div>
  );
}