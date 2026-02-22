import { useState, useEffect } from 'react';
import { DecisionSandbox } from './components/DecisionSandbox';
import { ImpactPanel } from './components/ImpactPanel';
import { SuccessTwinPanel } from './components/SuccessTwinPanel';
import {
  fetchCrises,
  simulateAftershock,
  AFTERSHOCK_ERROR_MESSAGE,
  fetchTwin,
  createMemo,
  type Crisis,
  type AftershockResult,
  type TwinResult,
  type MemoResponse,
} from '../lib/api';

const DEFAULT_PROJECT_ID = 'PRJ001';

export default function App() {
  const [crises, setCrises] = useState<Crisis[]>([]);
  const [crisesLoading, setCrisesLoading] = useState(true);
  const [crisesError, setCrisesError] = useState<string | null>(null);
  const [selectedCrisisId, setSelectedCrisisId] = useState<string | null>(null);
  
  // --- AFTERSHOCK STATE ---
  const [epicenter, setEpicenter] = useState('MLI');
  const [fundingAdjustment, setFundingAdjustment] = useState(-20);
  const [whatIfText, setWhatIfText] = useState('');
  const [timeHorizon, setTimeHorizon] = useState(12);

  const [simulationResult, setSimulationResult] = useState<AftershockResult | null>(null);
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
    setSimulationLoading(true);
    setSimulationError(null);

    try {
      const result = await simulateAftershock(
        epicenter,
        fundingAdjustment,
        timeHorizon
      );
      console.debug('Aftershock result:', result);
      setSimulationResult(result);
    } catch (err: unknown) {
      const message =
        err instanceof Error && err.message
          ? err.message
          : AFTERSHOCK_ERROR_MESSAGE;
      console.error('Aftershock simulation failed:', err);
      setSimulationError(message);
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
      // Backend requires simulation; we pass minimal TTC/equity placeholders when using aftershock-only flow
      const payload = {
        crisis_id: selectedCrisisId,
        simulation: {
          crisis_id: selectedCrisisId,
          metrics: {
            baseline_ttc_days: 0,
            scenario_ttc_days: 0,
            baseline_equity_shift_pct: 0,
            scenario_equity_shift_pct: 0,
            at_risk_population: 0,
          },
          impacted_regions: [],
        },
        scenario: {
          crisis_id: selectedCrisisId,
          funding_changes: [],
          shock: { inflation_pct: 0, drought: false, conflict_intensity: 0 },
          what_if_text: whatIfText || undefined,
        },
        twin: twinResult || undefined,
        aftershock: simulationResult,
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
    <div className="h-screen w-full bg-[#0a0e1a] text-gray-100 flex flex-col overflow-hidden">
      {/* Top Navigation */}
      <nav className="h-14 bg-[#0f1421] border-b border-gray-800 flex items-center justify-between px-6 shrink-0">
        <div className="text-xl tracking-tight">
          <span className="text-teal-400">Aid</span>
          <span className="text-gray-100">Sight</span>
          <span className="text-gray-500 ml-2 text-sm">Aftershock Sandbox</span>
        </div>
      </nav>

      {/* Main Content - Three Panels */}
      <div className="flex-1 flex overflow-hidden min-h-0">
        {/* Left: Configure Scenario */}
        <div className="w-[25%] bg-[#0f1421] border-r border-gray-800 overflow-y-auto shrink-0 flex flex-col">
          <div className="flex-1 overflow-y-auto">
          <DecisionSandbox
            epicenter={epicenter}
            setEpicenter={setEpicenter}
            fundingAdjustment={fundingAdjustment}
            setFundingAdjustment={setFundingAdjustment}
            timeHorizon={timeHorizon}
            setTimeHorizon={setTimeHorizon}
            onRunScenario={handleRunScenario}
            simulationLoading={simulationLoading}
          />
          </div>
        </div>

        {/* Center: Impact */}
        <div className="w-[45%] bg-[#0a0e1a] overflow-y-auto shrink-0 flex flex-col">
          <div className="px-6 py-4 border-b border-gray-800 shrink-0">
            <h2 className="text-base font-medium text-gray-100">Spillover Impact</h2>
            <p className="text-xs text-gray-500 mt-1">See regional displacement and cost inflation across borders.</p>
          </div>
          <div className="flex-1 overflow-y-auto">
          <ImpactPanel
            selectedCrisis={selectedCrisis}
            simulationResult={simulationResult}
            simulationLoading={simulationLoading}
            simulationError={simulationError}
            epicenter={epicenter}
            timeHorizon={timeHorizon}
          />
          </div>
        </div>

        {/* Right: Success Twin & Memo */}
        <div className="w-[30%] bg-[#0f1421] border-l border-gray-800 overflow-y-auto shrink-0 flex flex-col">
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