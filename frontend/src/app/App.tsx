import { useState, useEffect } from 'react';
import { DecisionSandbox } from './components/DecisionSandbox';
import { ImpactPanel } from './components/ImpactPanel';
import { SuccessTwinPanel } from './components/SuccessTwinPanel';
import {
  fetchCrises,
  simulate,
  fetchTwin,
  createMemo,
  type Crisis,
  type SimulationResult,
  type TwinResult,
  type MemoResponse,
  type ScenarioPayload,
} from '../lib/api';

// Default project ID for Success Twin (from projects.parquet)
const DEFAULT_PROJECT_ID = 'PRJ001';

export default function App() {
  const [crises, setCrises] = useState<Crisis[]>([]);
  const [crisesLoading, setCrisesLoading] = useState(true);
  const [crisesError, setCrisesError] = useState<string | null>(null);
  const [selectedCrisisId, setSelectedCrisisId] = useState<string | null>(null);
  const [healthDelta, setHealthDelta] = useState(0);
  const [washDelta, setWashDelta] = useState(0);
  const [inflationShock, setInflationShock] = useState(8);
  const [droughtShock, setDroughtShock] = useState(false);
  const [conflictIntensity, setConflictIntensity] = useState(0.3);
  const [whatIfText, setWhatIfText] = useState('');

  const [simulationResult, setSimulationResult] = useState<SimulationResult | null>(null);
  const [simulationLoading, setSimulationLoading] = useState(false);
  const [simulationError, setSimulationError] = useState<string | null>(null);

  const [twinResult, setTwinResult] = useState<TwinResult | null>(null);
  const [twinLoading, setTwinLoading] = useState(false);
  const [twinError, setTwinError] = useState<string | null>(null);

  const [memoResult, setMemoResult] = useState<MemoResponse | null>(null);
  const [memoLoading, setMemoLoading] = useState(false);
  const [memoError, setMemoError] = useState<string | null>(null);

  const loadCrises = () => {
    setCrisesLoading(true);
    setCrisesError(null);
    fetchCrises()
      .then((data) => {
        setCrises(data);
        if (data.length > 0 && !selectedCrisisId) setSelectedCrisisId(data[0].id);
        setCrisesError(null);
      })
      .catch((err) => {
        setCrisesError(err instanceof Error ? err.message : 'Failed to load crises');
        setCrises([]);
      })
      .finally(() => setCrisesLoading(false));
  };

  useEffect(() => {
    loadCrises();
  }, []);

  const selectedCrisis = crises.find((c) => c.id === selectedCrisisId);

  const handleRunScenario = async () => {
    if (!selectedCrisisId) return;
    setSimulationLoading(true);
    setSimulationError(null);
    try {
      const payload: ScenarioPayload = {
        crisis_id: selectedCrisisId,
        funding_changes: [
          { sector: 'Health', delta_usd: healthDelta },
          { sector: 'WASH', delta_usd: washDelta },
        ],
        shock: {
          inflation_pct: inflationShock,
          drought: droughtShock,
          conflict_intensity: conflictIntensity,
        },
        what_if_text: whatIfText || undefined,
      };
      const result = await simulate(selectedCrisisId, payload);
      setSimulationResult(result);
    } catch (err) {
      setSimulationError(err instanceof Error ? err.message : 'Simulation failed');
      setSimulationResult(null);
    } finally {
      setSimulationLoading(false);
    }
  };

  const handleFindTwin = async () => {
    setTwinLoading(true);
    setTwinError(null);
    try {
      const result = await fetchTwin(DEFAULT_PROJECT_ID);
      setTwinResult(result);
    } catch (err) {
      setTwinError(err instanceof Error ? err.message : 'Failed to find twin');
      setTwinResult(null);
    } finally {
      setTwinLoading(false);
    }
  };

  const handleGenerateMemo = async () => {
    if (!selectedCrisisId || !simulationResult) return;
    setMemoLoading(true);
    setMemoError(null);
    try {
      const payload = {
        crisis_id: selectedCrisisId,
        simulation: simulationResult,
        scenario: {
          crisis_id: selectedCrisisId,
          funding_changes: [
            { sector: 'Health', delta_usd: healthDelta },
            { sector: 'WASH', delta_usd: washDelta },
          ],
          shock: {
            inflation_pct: inflationShock,
            drought: droughtShock,
            conflict_intensity: conflictIntensity,
          },
          what_if_text: whatIfText || undefined,
        },
        twin: twinResult || undefined,
      };
      const result = await createMemo(payload);
      setMemoResult(result);
    } catch (err) {
      setMemoError(err instanceof Error ? err.message : 'Failed to generate memo');
      setMemoResult(null);
    } finally {
      setMemoLoading(false);
    }
  };

  return (
    <div className="size-full bg-[#0a0e1a] text-gray-100 flex flex-col overflow-hidden">
      {/* Top Navigation */}
      <nav className="h-14 bg-[#0f1421] border-b border-gray-800 flex items-center justify-between px-6 shrink-0">
        <div className="text-xl tracking-tight">
          <span className="text-teal-400">Aid</span>
          <span className="text-gray-100">Sight</span>
          <span className="text-gray-500 ml-2 text-sm">Strategy Sandbox</span>
        </div>
      </nav>

      {/* Main Content - Three Panels */}
      <div className="flex-1 flex overflow-hidden min-h-0">
        {/* Left: Configure Scenario */}
        <div className="w-[25%] bg-[#0f1421] border-r border-gray-800 overflow-y-auto shrink-0 flex flex-col">
          <div className="px-6 py-4 border-b border-gray-800 shrink-0">
            <h2 className="text-base font-medium text-gray-100">Configure Scenario</h2>
            <p className="text-xs text-gray-500 mt-1">Pick a crisis, adjust funding and shocks, then run.</p>
          </div>
          <div className="flex-1 overflow-y-auto">
          <DecisionSandbox
            crises={crises}
            selectedCrisisId={selectedCrisisId}
            setSelectedCrisisId={setSelectedCrisisId}
            healthDelta={healthDelta}
            setHealthDelta={setHealthDelta}
            washDelta={washDelta}
            setWashDelta={setWashDelta}
            inflationShock={inflationShock}
            setInflationShock={setInflationShock}
            droughtShock={droughtShock}
            setDroughtShock={setDroughtShock}
            conflictIntensity={conflictIntensity}
            setConflictIntensity={setConflictIntensity}
            whatIfText={whatIfText}
            setWhatIfText={setWhatIfText}
            onRunScenario={handleRunScenario}
            simulationLoading={simulationLoading}
            simulationError={simulationError}
            crisesLoading={crisesLoading}
            crisesError={crisesError}
            onRetryCrises={loadCrises}
          />
          </div>
        </div>

        {/* Center: Impact */}
        <div className="w-[45%] bg-[#0a0e1a] overflow-y-auto shrink-0 flex flex-col">
          <div className="px-6 py-4 border-b border-gray-800 shrink-0">
            <h2 className="text-base font-medium text-gray-100">Impact</h2>
            <p className="text-xs text-gray-500 mt-1">See baseline vs scenario TTC, Equity Shift, and regional impact.</p>
          </div>
          <div className="flex-1 overflow-y-auto">
          <ImpactPanel
            selectedCrisis={selectedCrisis}
            simulationResult={simulationResult}
            simulationLoading={simulationLoading}
          />
          </div>
        </div>

        {/* Right: Success Twin & Memo */}
        <div className="w-[30%] bg-[#0f1421] border-l border-gray-800 overflow-y-auto shrink-0 flex flex-col">
          <div className="px-6 py-4 border-b border-gray-800 shrink-0">
            <h2 className="text-base font-medium text-gray-100">Success Twin & Memo</h2>
            <p className="text-xs text-gray-500 mt-1">Find a similar project and generate AI analyst feedback.</p>
          </div>
          <div className="flex-1 overflow-y-auto min-h-0">
          <SuccessTwinPanel
            twinResult={twinResult}
            twinLoading={twinLoading}
            twinError={twinError}
            onFindTwin={handleFindTwin}
            memoResult={memoResult}
            memoLoading={memoLoading}
            memoError={memoError}
            onGenerateMemo={handleGenerateMemo}
            canGenerateMemo={!!simulationResult}
          />
          </div>
        </div>
      </div>
    </div>
  );
}
