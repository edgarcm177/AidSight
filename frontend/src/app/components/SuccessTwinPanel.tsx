import { useState } from 'react';
import type { TwinResult, MemoResponse } from '../../lib/api';

interface SuccessTwinPanelProps {
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

export function SuccessTwinPanel({
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

  // NEW: Broadcast a custom event when a country is clicked
  const handleCountryClick = (iso: string) => {
    window.dispatchEvent(new CustomEvent('FOCUS_MAP_COUNTRY', { detail: iso }));
  };

  return (
    <div className="flex flex-col h-full bg-[#0f1421]">
      <div className="flex border-b border-gray-800 shrink-0 px-2 pt-2">
        <button
          onClick={() => setActiveTab('impact')}
          className={`px-4 py-3 text-sm font-medium transition-colors border-b-2 ${
            activeTab === 'impact' ? 'border-teal-500 text-teal-400' : 'border-transparent text-gray-500 hover:text-gray-300'
          }`}
        >
          Spillover Impact
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
              <div className="space-y-3">
                {/* Notice the new onClick handlers here! */}
                <div onClick={() => handleCountryClick('NER')} className="bg-[#1a1f2e] border border-gray-800 rounded p-3 cursor-pointer hover:border-gray-500 transition-colors">
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-medium text-gray-200">1. Niger</span>
                    <span className="text-red-400 text-sm font-mono">+45k displaced</span>
                  </div>
                  <div className="text-xs text-amber-400 font-mono">+$8.1M response cost</div>
                </div>

                <div onClick={() => handleCountryClick('BFA')} className="bg-[#1a1f2e] border border-gray-800 rounded p-3 cursor-pointer hover:border-gray-500 transition-colors">
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-medium text-gray-200">2. Burkina Faso</span>
                    <span className="text-red-400 text-sm font-mono">+37k displaced</span>
                  </div>
                  <div className="text-xs text-amber-400 font-mono">+$6.2M response cost</div>
                </div>

                <div onClick={() => handleCountryClick('TCD')} className="bg-[#1a1f2e] border border-gray-800 rounded p-3 cursor-pointer hover:border-gray-500 transition-colors">
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-medium text-gray-200">3. Chad</span>
                    <span className="text-red-400 text-sm font-mono">+30k displaced</span>
                  </div>
                  <div className="text-xs text-amber-400 font-mono">+$4.1M response cost</div>
                </div>
              </div>
            </section>

            <section className="mt-8 bg-[#0a0e1a] border border-gray-800 rounded-lg p-4">
              <h3 className="text-xs uppercase tracking-wider text-teal-600 mb-2">AI Summary</h3>
              <p className="text-sm text-gray-400 leading-relaxed">
                Cutting 20% from Mali's crisis today is projected to push 112k additional people into neighboring countries within 12 months, increasing regional response costs by $24M.
              </p>
            </section>
          </div>
        )}

        {activeTab === 'ai' && (
          <div className="space-y-8">
            <section>
              <h3 className="text-xs uppercase tracking-wider text-gray-500 mb-4">Success Twin</h3>
              <div className="bg-[#1a1f2e] border border-gray-800 rounded-lg p-4">
                <button onClick={onFindTwin} disabled={twinLoading} className="text-teal-400 hover:text-teal-300 text-sm font-medium transition-colors">
                  {twinLoading ? 'Searching...' : 'Find Success Twin ↗'}
                </button>
                {twinResult && (
                  <div className="mt-4 pt-4 border-t border-gray-800 text-sm text-gray-300">Twin Found: <span className="font-mono text-teal-400">{twinResult.project_id}</span></div>
                )}
              </div>
            </section>

            <section>
              <h3 className="text-xs uppercase tracking-wider text-gray-500 mb-4">Contrarian Decision Memo</h3>
              <div className="bg-[#1a1f2e] border border-gray-800 rounded-lg p-4 flex flex-col h-[250px]">
                <div className="flex-1 overflow-y-auto mb-4 text-sm text-gray-400">
                  {memoLoading ? <p className="animate-pulse">Analyzing risk factors...</p> : memoResult ? <p>{memoResult.memo}</p> : <p>Run a scenario first.</p>}
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