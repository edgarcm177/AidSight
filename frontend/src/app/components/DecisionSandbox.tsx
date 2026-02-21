import { ChevronDown } from 'lucide-react';
import type { Crisis } from '../../lib/api';

interface DecisionSandboxProps {
  crises: Crisis[];
  crisesLoading: boolean;
  crisesError: string | null;
  onRetryCrises: () => void;
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
  crisesLoading,
  crisesError,
  onRetryCrises,
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
  const hasCrisis = !!selectedCrisisId;
  const formatUsd = (n: number) =>
    `${n >= 0 ? '+' : ''}${(n / 1_000_000).toFixed(1)}M`;

  return (
    <div className="p-6">
      {/* Crisis Selection */}
      <section className="mb-8">
        <h2 className="text-xs uppercase tracking-wider text-gray-500 mb-3">Crisis Selection</h2>
        {crisesLoading ? (
          <div className="py-8 text-center text-sm text-gray-500">Loading crises…</div>
        ) : crisesError ? (
          <div className="p-4 bg-red-900/30 border border-red-700 rounded-lg">
            <p className="text-sm text-red-300 mb-3">{crisesError}</p>
            <button
              onClick={onRetryCrises}
              className="w-full py-2 rounded text-sm bg-red-800/50 hover:bg-red-800/70 text-red-200 focus:outline-none focus:ring-2 focus:ring-teal-500"
            >
              Retry
            </button>
          </div>
        ) : (
        <div className="relative">
          <select
            value={selectedCrisisId ?? ''}
            onChange={(e) => setSelectedCrisisId(e.target.value)}
            disabled={crises.length === 0}
            aria-label="Select a crisis"
            className="w-full bg-[#1a1f2e] border border-gray-700 rounded px-3 py-2.5 text-sm text-gray-200 appearance-none cursor-pointer hover:border-gray-600 transition-colors focus:outline-none focus:ring-2 focus:ring-teal-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {crises.length === 0 ? (
              <option value="">No crises</option>
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
        )}
      </section>

      {/* Funding Changes (deltas in USD) */}
      <section className={`mb-8 ${!hasCrisis ? 'opacity-60 pointer-events-none' : ''}`}>
        <h2 className="text-xs uppercase tracking-wider text-gray-500 mb-1">Funding Changes</h2>
        <p className="text-xs text-gray-600 mb-4">Change in Health and WASH funding for this crisis (USD)</p>
        <div className="mb-5">
          <div className="flex justify-between items-center mb-2">
            <label className="text-sm text-gray-300">Health Δ (USD)</label>
            <span className="text-sm text-teal-400 font-mono">{formatUsd(healthDelta)}</span>
          </div>
          <input
            type="range"
            min="-10000000"
            max="10000000"
            step="250000"
            value={healthDelta}
            onChange={(e) => setHealthDelta(Number(e.target.value))}
            disabled={!hasCrisis}
            aria-label="Health funding delta"
            className="w-full h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer slider disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 focus:ring-offset-[#0f1421]"
          />
        </div>
        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="text-sm text-gray-300">WASH Δ (USD)</label>
            <span className="text-sm text-teal-400 font-mono">{formatUsd(washDelta)}</span>
          </div>
          <input
            type="range"
            min="-10000000"
            max="10000000"
            step="250000"
            value={washDelta}
            onChange={(e) => setWashDelta(Number(e.target.value))}
            disabled={!hasCrisis}
            aria-label="WASH funding delta"
            className="w-full h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer slider disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 focus:ring-offset-[#0f1421]"
          />
        </div>
      </section>

      {/* Shocks */}
      <section className={`mb-8 ${!hasCrisis ? 'opacity-60 pointer-events-none' : ''}`}>
        <h2 className="text-xs uppercase tracking-wider text-gray-500 mb-1">Shocks</h2>
        <p className="text-xs text-gray-600 mb-4">External stressors applied to the scenario</p>
        <div className="mb-5">
          <div className="flex justify-between items-center mb-2">
            <label className="text-sm text-gray-300">Inflation (%)</label>
            <span className="text-sm text-amber-400 font-mono">{inflationShock}% (0–50)</span>
          </div>
          <input
            type="range"
            min="0"
            max="50"
            step="1"
            value={inflationShock}
            onChange={(e) => setInflationShock(Number(e.target.value))}
            disabled={!hasCrisis}
            aria-label="Inflation shock percentage"
            className="w-full h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer slider disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 focus:ring-offset-[#0f1421]"
          />
        </div>
        <div className="mb-5">
          <div className="flex justify-between items-center">
            <div>
              <label className="text-sm text-gray-300">Drought?</label>
              <p className="text-xs text-gray-600 mt-0.5">Climate stress on water/infrastructure</p>
            </div>
            <button
              onClick={() => hasCrisis && setDroughtShock(!droughtShock)}
              disabled={!hasCrisis}
              aria-label="Toggle drought shock"
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 focus:ring-offset-[#0f1421] disabled:opacity-50 ${
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
            <label className="text-sm text-gray-300">Conflict level</label>
            <span className="text-sm text-red-400 font-mono">{conflictIntensity.toFixed(2)} (0–1)</span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={conflictIntensity}
            onChange={(e) => setConflictIntensity(Number(e.target.value))}
            disabled={!hasCrisis}
            aria-label="Conflict intensity 0 to 1"
            className="w-full h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer slider disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 focus:ring-offset-[#0f1421]"
          />
        </div>
      </section>

      {/* What-if Description */}
      <section className={`mb-6 ${!hasCrisis ? 'opacity-60 pointer-events-none' : ''}`}>
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
        disabled={!hasCrisis || simulationLoading}
        aria-label={!hasCrisis ? 'Select a crisis first' : 'Run scenario'}
        title={!hasCrisis ? 'Select a crisis first' : undefined}
        className="w-full bg-teal-600 hover:bg-teal-500 disabled:opacity-50 disabled:cursor-not-allowed text-white py-3 rounded text-sm tracking-wide transition-colors focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 focus:ring-offset-[#0f1421]"
      >
        {simulationLoading ? 'Running scenario…' : 'Run Scenario'}
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
