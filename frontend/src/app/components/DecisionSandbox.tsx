import { ChevronDown } from 'lucide-react';

interface DecisionSandboxProps {
  epicenter: string;
  setEpicenter: (value: string) => void;
  fundingAdjustment: number;
  setFundingAdjustment: (value: number) => void;
  timeHorizon: number;
  setTimeHorizon: (value: number) => void;
  onRunScenario: () => void;
  simulationLoading: boolean;
}

export function DecisionSandbox({
  epicenter,
  setEpicenter,
  fundingAdjustment,
  setFundingAdjustment,
  timeHorizon,
  setTimeHorizon,
  onRunScenario,
  simulationLoading,
}: DecisionSandboxProps) {
  
  return (
    <div className="p-6">
      <h2 className="text-sm font-semibold tracking-wide text-gray-100 mb-6">Configure Aftershock</h2>

      {/* Epicenter Selection */}
      <section className="mb-8">
        <h3 className="text-xs uppercase tracking-wider text-gray-500 mb-3">Epicenter Crisis (Country-Year)</h3>
        <div className="relative">
          <select
            value={epicenter}
            onChange={(e) => setEpicenter(e.target.value)}
            className="w-full bg-[#1a1f2e] border border-gray-700 rounded px-3 py-3 text-sm text-gray-200 appearance-none cursor-pointer hover:border-gray-600 transition-colors focus:outline-none focus:ring-2 focus:ring-teal-500"
          >
            <option value="">Select epicenter…</option>
            <option value="AFG">Afghanistan (2024)</option>
            <option value="AGO">Angola (2024)</option>
            <option value="BEN">Benin (2024)</option>
            <option value="BFA">Burkina Faso (2024)</option>
            <option value="BDI">Burundi (2024)</option>
            <option value="CMR">Cameroon (2024)</option>
            <option value="CAF">Central African Republic (2024)</option>
            <option value="TCD">Chad (2024)</option>
            <option value="COD">DR Congo (2024)</option>
            <option value="COG">Congo (2024)</option>
            <option value="CIV">Côte d'Ivoire (2024)</option>
            <option value="ERI">Eritrea (2024)</option>
            <option value="ETH">Ethiopia (2024)</option>
            <option value="GMB">Gambia (2024)</option>
            <option value="GHA">Ghana (2024)</option>
            <option value="GIN">Guinea (2024)</option>
            <option value="GNB">Guinea-Bissau (2024)</option>
            <option value="IRQ">Iraq (2024)</option>
            <option value="KEN">Kenya (2024)</option>
            <option value="LBR">Liberia (2024)</option>
            <option value="LBY">Libya (2024)</option>
            <option value="MLI">Mali (2024)</option>
            <option value="MRT">Mauritania (2024)</option>
            <option value="MOZ">Mozambique (2024)</option>
            <option value="MMR">Myanmar (2024)</option>
            <option value="NER">Niger (2024)</option>
            <option value="NGA">Nigeria (2024)</option>
            <option value="PRK">North Korea (2024)</option>
            <option value="PAK">Pakistan (2024)</option>
            <option value="PSE">Palestine (2024)</option>
            <option value="RWA">Rwanda (2024)</option>
            <option value="SEN">Senegal (2024)</option>
            <option value="SLE">Sierra Leone (2024)</option>
            <option value="SOM">Somalia (2024)</option>
            <option value="SSD">South Sudan (2024)</option>
            <option value="SDN">Sudan (2024)</option>
            <option value="SYR">Syria (2024)</option>
            <option value="TZA">Tanzania (2024)</option>
            <option value="TGO">Togo (2024)</option>
            <option value="UGA">Uganda (2024)</option>
            <option value="UKR">Ukraine (2024)</option>
            <option value="YEM">Yemen (2024)</option>
            <option value="ZMB">Zambia (2024)</option>
            <option value="ZWE">Zimbabwe (2024)</option>
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
        </div>
      </section>

      {/* Funding Adjustment Slider */}
      <section className="mb-10">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xs uppercase tracking-wider text-gray-500">Funding Change for Epicenter</h3>
          <span className={`text-sm font-mono font-bold ${fundingAdjustment < 0 ? 'text-red-400' : 'text-teal-400'}`}>
            {fundingAdjustment > 0 ? '+' : ''}{fundingAdjustment}%
          </span>
        </div>
        
        <div className="relative px-1">
          <input
            type="range"
            min="-20"
            max="20"
            step="1"
            value={fundingAdjustment}
            onChange={(e) => setFundingAdjustment(Number(e.target.value))}
            className="w-full h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer slider focus:outline-none"
          />
          <div className="flex justify-between text-[10px] text-gray-600 mt-2 font-mono">
            <span>-20% (Cut)</span>
            <span>0%</span>
            <span>+20% (Boost)</span>
          </div>
        </div>
      </section>

      {/* Timeline Slider */}
      <section className="mb-10">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xs uppercase tracking-wider text-gray-500">Time Horizon</h3>
          <span className="text-sm font-mono font-bold text-teal-400">
            {timeHorizon} Months
          </span>
        </div>
        
        <div className="relative px-1">
          <input
            type="range"
            min="0"
            max="12"
            step="1"
            value={timeHorizon}
            onChange={(e) => setTimeHorizon(Number(e.target.value))}
            className="w-full h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer slider focus:outline-none"
          />
          <div className="flex justify-between text-[10px] text-gray-600 mt-2 font-mono">
            <span>0m</span>
            <span>6m</span>
            <span>12m</span>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            {timeHorizon <= 6 ? "Short-term impact (≈1 year)" : "Medium-term impact (≈2 years)"}
          </p>
        </div>
      </section>

      {/* Run Button */}
      <button
        onClick={onRunScenario}
        disabled={simulationLoading || !epicenter}
        className="w-full bg-teal-600 hover:bg-teal-500 disabled:opacity-50 disabled:cursor-not-allowed text-white py-3.5 rounded text-sm font-semibold tracking-wide transition-colors focus:outline-none focus:ring-2 focus:ring-teal-500"
      >
        {simulationLoading ? 'Running…' : 'Run Aftershock'}
      </button>

      {/* Custom Slider CSS directly injected */}
      <style>{`
        .slider::-webkit-slider-thumb {
          appearance: none;
          width: 16px;
          height: 16px;
          border-radius: 2px;
          background: ${fundingAdjustment < 0 ? '#f87171' : '#14b8a6'};
          cursor: pointer;
        }
        .slider::-moz-range-thumb {
          width: 16px;
          height: 16px;
          border-radius: 2px;
          background: ${fundingAdjustment < 0 ? '#f87171' : '#14b8a6'};
          cursor: pointer;
          border: none;
        }
      `}</style>
    </div>
  );
}