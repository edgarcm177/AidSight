import { ChevronDown } from 'lucide-react';
import type { Crisis } from '../../lib/api';

interface DecisionSandboxProps {
  crises: Crisis[];
  selectedCrisisId: string | null;
  setSelectedCrisisId: (id: string) => void;
  healthDelta: number;
  setHealthDelta: (value: number) => void;
  washDelta: number;
  setWashDelta: (value: number) => void;
  inflationShock: number;
  setInflationShock: (value: number) => void;
  droughtShock: boolean;
  setDroughtShock: (value: boolean) => void;
  conflictIntensity: number;
  setConflictIntensity: (value: number) => void;
  whatIfText: string;
  setWhatIfText: (value: string) => void;
  onRunScenario: () => void;
  simulationLoading: boolean;
  simulationError: string | null;
}

export function DecisionSandbox({
  crises,
  selectedCrisisId,
  setSelectedCrisisId,
  healthDelta,
  setHealthDelta,
  washDelta,
  setWashDelta,
  inflationShock,
  setInflationShock,
  droughtShock,
  setDroughtShock,
  conflictIntensity,
  setConflictIntensity,
  whatIfText,
  setWhatIfText,
  onRunScenario,
  simulationLoading,
  simulationError,
}: DecisionSandboxProps) {
  return (
    <div className="p-6">
      <h1 className="text-lg mb-6 tracking-tight text-gray-100">Decision Sandbox</h1>

      {/* Crisis Selection */}
      <section className="mb-8">
        <h2 className="text-xs uppercase tracking-wider text-gray-500 mb-3">Crisis Selection</h2>
        <div className="relative">
          <select
            value={selectedCrisisId ?? ''}
            onChange={(e) => setSelectedCrisisId(e.target.value)}
            disabled={crises.length === 0}
            className="w-full bg-[#1a1f2e] border border-gray-700 rounded px-3 py-2.5 text-sm text-gray-200 appearance-none cursor-pointer hover:border-gray-600 transition-colors focus:outline-none focus:border-teal-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {crises.length === 0 ? (
              <option value="">Loading crises...</option>
            ) : (
              crises.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.country} {c.year})
                </option>
              ))
            )}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
        </div>
      </section>

      {/* Funding Changes (deltas in USD) */}
      <section className="mb-8">
        <h2 className="text-xs uppercase tracking-wider text-gray-500 mb-4">Funding Changes (Δ USD)</h2>
        <div className="mb-5">
          <div className="flex justify-between items-center mb-2">
            <label className="text-sm text-gray-300">Health Δ (USD)</label>
            <span className="text-sm text-teal-400 font-mono">
              {healthDelta >= 0 ? '+' : ''}
              {(healthDelta / 1_000_000).toFixed(1)}M
            </span>
          </div>
          <input
            type="range"
            min="-10000000"
            max="10000000"
            step="250000"
            value={healthDelta}
            onChange={(e) => setHealthDelta(Number(e.target.value))}
            className="w-full h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer slider"
          />
        </div>
        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="text-sm text-gray-300">WASH Δ (USD)</label>
            <span className="text-sm text-teal-400 font-mono">
              {washDelta >= 0 ? '+' : ''}
              {(washDelta / 1_000_000).toFixed(1)}M
            </span>
          </div>
          <input
            type="range"
            min="-10000000"
            max="10000000"
            step="250000"
            value={washDelta}
            onChange={(e) => setWashDelta(Number(e.target.value))}
            className="w-full h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer slider"
          />
        </div>
      </section>

      {/* Shocks */}
      <section className="mb-8">
        <h2 className="text-xs uppercase tracking-wider text-gray-500 mb-4">Shocks</h2>
        <div className="mb-5">
          <div className="flex justify-between items-center mb-2">
            <label className="text-sm text-gray-300">Inflation shock (%)</label>
            <span className="text-sm text-amber-400 font-mono">{inflationShock}%</span>
          </div>
          <input
            type="range"
            min="0"
            max="50"
            step="1"
            value={inflationShock}
            onChange={(e) => setInflationShock(Number(e.target.value))}
            className="w-full h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer slider"
          />
        </div>
        <div className="mb-5">
          <div className="flex justify-between items-center">
            <label className="text-sm text-gray-300">Drought shock</label>
            <button
              onClick={() => setDroughtShock(!droughtShock)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                droughtShock ? 'bg-teal-600' : 'bg-gray-700'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  droughtShock ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        </div>
        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="text-sm text-gray-300">Conflict intensity</label>
            <span className="text-sm text-red-400 font-mono">{conflictIntensity.toFixed(2)}</span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={conflictIntensity}
            onChange={(e) => setConflictIntensity(Number(e.target.value))}
            className="w-full h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer slider"
          />
        </div>
      </section>

      {/* What-if Description */}
      <section className="mb-6">
        <h2 className="text-xs uppercase tracking-wider text-gray-500 mb-3">What-if Description</h2>
        <textarea
          value={whatIfText}
          onChange={(e) => setWhatIfText(e.target.value)}
          placeholder="Describe a What-If scenario..."
          className="w-full bg-[#1a1f2e] border border-gray-700 rounded px-3 py-2.5 text-sm text-gray-200 placeholder-gray-600 resize-none h-24 focus:outline-none focus:border-teal-500 transition-colors"
        />
      </section>

      {/* Error */}
      {simulationError && (
        <div className="mb-4 p-3 bg-red-900/30 border border-red-700 rounded text-sm text-red-300">
          {simulationError}
        </div>
      )}

      {/* Run Scenario Button */}
      <button
        onClick={onRunScenario}
        disabled={!selectedCrisisId || simulationLoading}
        className="w-full bg-teal-600 hover:bg-teal-500 disabled:opacity-50 disabled:cursor-not-allowed text-white py-3 rounded text-sm tracking-wide transition-colors"
      >
        {simulationLoading ? 'Running...' : 'Run Scenario'}
      </button>

      <style>{`
        .slider::-webkit-slider-thumb {
          appearance: none;
          width: 14px;
          height: 14px;
          border-radius: 50%;
          background: #14b8a6;
          cursor: pointer;
        }
        .slider::-moz-range-thumb {
          width: 14px;
          height: 14px;
          border-radius: 50%;
          background: #14b8a6;
          cursor: pointer;
          border: none;
        }
      `}</style>
    </div>
  );
}
