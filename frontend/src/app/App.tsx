import { useState } from 'react';
import { DecisionSandbox } from './components/DecisionSandbox';
import { ImpactPanel } from './components/ImpactPanel';
import { SuccessTwinPanel } from './components/SuccessTwinPanel';

export default function App() {
  const [crisisRegion, setCrisisRegion] = useState('somalia-drought-2024');
  const [healthFunding, setHealthFunding] = useState(5000000);
  const [washFunding, setWashFunding] = useState(3000000);
  const [inflationShock, setInflationShock] = useState(8);
  const [droughtShock, setDroughtShock] = useState(false);
  const [conflictIntensity, setConflictIntensity] = useState(0.3);
  const [whatIfText, setWhatIfText] = useState('');
  const [scenarioRun, setScenarioRun] = useState(false);

  const handleRunScenario = () => {
    setScenarioRun(true);
    // In a real app, this would trigger API calls and data updates
  };

  return (
    <div className="size-full bg-[#0a0e1a] text-gray-100 flex flex-col overflow-hidden">
      {/* Top Navigation */}
      <nav className="h-14 bg-[#0f1421] border-b border-gray-800 flex items-center justify-between px-6">
        <div className="text-xl tracking-tight">
          <span className="text-teal-400">Aid</span>
          <span className="text-gray-100">Sight</span>
          <span className="text-gray-500 ml-2 text-sm">Strategy Sandbox</span>
        </div>
        <button className="text-sm text-gray-400 hover:text-gray-200 transition-colors">
          Scenario History
        </button>
      </nav>

      {/* Main Content - Three Panels */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Decision Sandbox */}
        <div className="w-[25%] bg-[#0f1421] border-r border-gray-800 overflow-y-auto">
          <DecisionSandbox
            crisisRegion={crisisRegion}
            setCrisisRegion={setCrisisRegion}
            healthFunding={healthFunding}
            setHealthFunding={setHealthFunding}
            washFunding={washFunding}
            setWashFunding={setWashFunding}
            inflationShock={inflationShock}
            setInflationShock={setInflationShock}
            droughtShock={droughtShock}
            setDroughtShock={setDroughtShock}
            conflictIntensity={conflictIntensity}
            setConflictIntensity={setConflictIntensity}
            whatIfText={whatIfText}
            setWhatIfText={setWhatIfText}
            onRunScenario={handleRunScenario}
          />
        </div>

        {/* Center Panel - Impact & Fragility */}
        <div className="w-[45%] bg-[#0a0e1a] overflow-y-auto">
          <ImpactPanel
            scenarioRun={scenarioRun}
            healthFunding={healthFunding}
            washFunding={washFunding}
            inflationShock={inflationShock}
            droughtShock={droughtShock}
            conflictIntensity={conflictIntensity}
          />
        </div>

        {/* Right Panel - Success Twin & Contrarian Memo */}
        <div className="w-[30%] bg-[#0f1421] border-l border-gray-800 overflow-y-auto">
          <SuccessTwinPanel
            scenarioRun={scenarioRun}
            inflationShock={inflationShock}
            droughtShock={droughtShock}
          />
        </div>
      </div>
    </div>
  );
}
