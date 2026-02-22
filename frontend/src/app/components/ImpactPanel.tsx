import { useRef, useEffect } from 'react';
// @ts-ignore
import csvDataUrl from '../../../../dataml/data/raw/misfit_final_analysis.csv';
import type { Crisis, SimulationResult } from '../../lib/api';

interface ImpactPanelProps {
  selectedCrisis: Crisis | undefined;
  simulationResult: SimulationResult | null;
  simulationLoading: boolean;
  epicenter: string;
  timeHorizon: number;
}

export function ImpactPanel({
  selectedCrisis,
  simulationResult,
  simulationLoading,
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

      {!hasScenario && !simulationLoading ? (
        <div className="mb-6 p-6 bg-[#0f1421] border border-gray-800 rounded-lg text-center">
          <p className="text-sm text-gray-500">Run a scenario to see impact.</p>
          <p className="text-xs text-gray-600 mt-2">Adjust funding and click Run Aftershock.</p>
        </div>
      ) : (
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-[#0f1421] border border-gray-800 rounded-lg p-4 border-t-2 border-t-red-500">
          <div className="text-xs text-gray-500 mb-2 uppercase tracking-wider">Extra displaced (region)</div>
          <div className="text-2xl text-red-400 font-mono">{simulationLoading ? '...' : '+112,000'}</div>
          <div className="text-xs text-gray-600 mt-1">across 3 neighboring countries at T+{timeHorizon}m</div>
        </div>

        <div className="bg-[#0f1421] border border-gray-800 rounded-lg p-4 border-t-2 border-t-amber-500">
          <div className="text-xs text-gray-500 mb-2 uppercase tracking-wider">Extra response cost</div>
          <div className="text-2xl text-amber-400 font-mono">{simulationLoading ? '...' : '+$24.0M'}</div>
          <div className="text-xs text-gray-600 mt-1">projected additional funding needed</div>
        </div>

        <div className="bg-[#0f1421] border border-gray-800 rounded-lg p-4 border-t-2 border-t-teal-500">
          <div className="text-xs text-gray-500 mb-2 uppercase tracking-wider">New underfunded crises</div>
          <div className="text-2xl text-gray-100 font-mono">{simulationLoading ? '...' : '+2'}</div>
          <div className="text-xs text-gray-600 mt-1">countries crossing underfunded threshold</div>
        </div>
      </div>
      )}
    </div>
  );
}