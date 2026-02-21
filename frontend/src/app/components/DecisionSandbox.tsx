import { ChevronDown } from 'lucide-react';

interface DecisionSandboxProps {
  crisisRegion: string;
  setCrisisRegion: (value: string) => void;
  healthFunding: number;
  setHealthFunding: (value: number) => void;
  washFunding: number;
  setWashFunding: (value: number) => void;
  inflationShock: number;
  setInflationShock: (value: number) => void;
  droughtShock: boolean;
  setDroughtShock: (value: boolean) => void;
  conflictIntensity: number;
  setConflictIntensity: (value: number) => void;
  whatIfText: string;
  setWhatIfText: (value: string) => void;
  onRunScenario: () => void;
}

export function DecisionSandbox({
  crisisRegion,
  setCrisisRegion,
  healthFunding,
  setHealthFunding,
  washFunding,
  setWashFunding,
  inflationShock,
  setInflationShock,
  droughtShock,
  setDroughtShock,
  conflictIntensity,
  setConflictIntensity,
  whatIfText,
  setWhatIfText,
  onRunScenario,
}: DecisionSandboxProps) {
  return (
    <div className="p-6">
      <h1 className="text-lg mb-6 tracking-tight text-gray-100">Decision Sandbox</h1>

      {/* Crisis Selection */}
      <section className="mb-8">
        <h2 className="text-xs uppercase tracking-wider text-gray-500 mb-3">Crisis Selection</h2>
        <div className="relative">
          <select
            value={crisisRegion}
            onChange={(e) => setCrisisRegion(e.target.value)}
            className="w-full bg-[#1a1f2e] border border-gray-700 rounded px-3 py-2.5 text-sm text-gray-200 appearance-none cursor-pointer hover:border-gray-600 transition-colors focus:outline-none focus:border-teal-500"
          >
            <option value="somalia-drought-2024">Somalia Drought Crisis 2024</option>
            <option value="sudan-conflict-2024">Sudan Conflict Zone 2024</option>
            <option value="afghanistan-winter-2024">Afghanistan Winter Emergency 2024</option>
            <option value="yemen-cholera-2024">Yemen Cholera Outbreak 2024</option>
            <option value="ethiopia-tigray-2024">Ethiopia Tigray Region 2024</option>
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
        </div>
      </section>

      {/* Funding Changes */}
      <section className="mb-8">
        <h2 className="text-xs uppercase tracking-wider text-gray-500 mb-4">Funding Changes</h2>
        
        <div className="mb-5">
          <div className="flex justify-between items-center mb-2">
            <label className="text-sm text-gray-300">Health funding Δ (USD)</label>
            <span className="text-sm text-teal-400 font-mono">${(healthFunding / 1000000).toFixed(1)}M</span>
          </div>
          <input
            type="range"
            min="0"
            max="20000000"
            step="500000"
            value={healthFunding}
            onChange={(e) => setHealthFunding(Number(e.target.value))}
            className="w-full h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer slider"
          />
        </div>

        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="text-sm text-gray-300">WASH funding Δ (USD)</label>
            <span className="text-sm text-teal-400 font-mono">${(washFunding / 1000000).toFixed(1)}M</span>
          </div>
          <input
            type="range"
            min="0"
            max="15000000"
            step="500000"
            value={washFunding}
            onChange={(e) => setWashFunding(Number(e.target.value))}
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

      {/* Run Scenario Button */}
      <button
        onClick={onRunScenario}
        className="w-full bg-teal-600 hover:bg-teal-500 text-white py-3 rounded text-sm tracking-wide transition-colors"
      >
        Run Scenario
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
