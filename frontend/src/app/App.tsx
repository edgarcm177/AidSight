import { useState, useEffect } from 'react';
import { DecisionSandbox } from './components/DecisionSandbox';
import { ImpactPanel } from './components/ImpactPanel';
import { SuccessTwinPanel } from './components/SuccessTwinPanel';
import {
  fetchCrises,
  fetchProjectForCrisis,
  simulateAftershock,
  AFTERSHOCK_ERROR_MESSAGE,
  fetchTwin,
  createMemo,
  type Crisis,
  type AftershockResult,
  type TwinResult,
  type MemoResponse,
  type CrisisProjectResponse,
} from '../lib/api';
import { reportDiagnostics } from '../lib/diagnostics';

const CRISIS_YEAR = 2024; // Epicenter dropdown options are e.g. "Mali (2024)"

export default function App() {
  const [crises, setCrises] = useState<Crisis[]>([]);
  const [crisesLoading, setCrisesLoading] = useState(true);
  const [crisesError, setCrisesError] = useState<string | null>(null);
  const [selectedCrisisId, setSelectedCrisisId] = useState<string | null>(null);

  /** Project for selected epicenter (exact or nearest fallback). Null only when no projects in dataset. */
  const [crisisProject, setCrisisProject] = useState<CrisisProjectResponse | null>(null);

  // --- AFTERSHOCK STATE ---
  const [epicenter, setEpicenter] = useState('');
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

  useEffect(() => {
    if (!epicenter?.trim()) {
      setCrisisProject(null);
      return;
    }
    fetchProjectForCrisis(epicenter, CRISIS_YEAR)
      .then(setCrisisProject)
      .catch(() => setCrisisProject(null));
  }, [epicenter]);

  const handleEpicenterChange = (value: string) => {
    setEpicenter(value);
    setSimulationResult(null);
    setSimulationError(null);
    setTwinResult(null);
    setTwinError(null);
    setMemoResult(null);
    setMemoError(null);
  };

  // When funding or time horizon changes, clear simulation so user must run again for new metrics
  useEffect(() => {
    setSimulationResult(null);
    setSimulationError(null);
    setTwinResult(null);
    setTwinError(null);
    setMemoResult(null);
    setMemoError(null);
  }, [fundingAdjustment, timeHorizon]);

  useEffect(() => {
    reportDiagnostics({
      impactCards: {
        source: simulationResult ? 'LIVE' : 'PLACEHOLDER',
        simulationResult: !!simulationResult,
        epicenter: simulationResult?.epicenter,
        totalDisplaced: simulationResult?.totals.total_delta_displaced,
        totalCost: simulationResult?.totals.total_extra_cost_usd,
        affectedCount: simulationResult?.totals.affected_countries,
      },
      affectedCountries: {
        source: simulationResult?.affected?.length ? 'LIVE' : 'PLACEHOLDER',
        count: simulationResult?.affected?.length ?? 0,
        countries: simulationResult?.affected?.map((a) => a.country),
      },
      aiSummary: {
        source: simulationResult?.totals ? 'LIVE' : 'PLACEHOLDER',
      },
      map: {
        status: simulationResult?.affected?.length ? 'LIVE' : 'PLACEHOLDER',
        epicenterSent: simulationResult?.epicenter,
        affectedSent: simulationResult?.affected?.map((a) => a.country),
        message: simulationResult?.affected?.length
          ? `epicenter=${simulationResult.epicenter}, affected=${simulationResult.affected.map((a) => a.country).join(', ')}`
          : 'No AFTERSHOCK_AFFECTED sent yet',
      },
      successTwin: {
        source: twinResult ? 'LIVE' : 'PLACEHOLDER',
        projectId: twinResult?.twin_project_id,
      },
      vectorNeighbors: { source: 'API_PENDING', count: 0 },
      memo: {
        source: memoResult ? 'LIVE' : 'PLACEHOLDER',
      },
      sphinx: { source: 'API_PENDING' },
    });
  }, [simulationResult, twinResult, memoResult]);

  const handleRunScenario = async () => {
    setSimulationLoading(true);
    setSimulationError(null);

    try {
      const result = await simulateAftershock({
        epicenter,
        delta_funding_pct: fundingAdjustment / 100,
        horizon_steps: timeHorizon <= 6 ? 1 : 2,
      });
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
      if (!crisisProject?.id) return;
      const result = await fetchTwin(crisisProject.id);
      setTwinResult(result);
    } catch (err) {
      setTwinError(err instanceof Error ? err.message : 'Failed to find twin');
      setTwinResult(null);
    } finally {
      setTwinLoading(false);
    }
  };

  const handleGenerateMemo = async () => {
    if (!simulationResult) return;
    const crisisId = selectedCrisisId ?? `${simulationResult.epicenter}${simulationResult.baseline_year}`;
    setMemoLoading(true);
    setMemoError(null);
    try {
      // Backend requires simulation; we pass minimal TTC/equity placeholders when using aftershock-only flow
      const payload = {
        crisis_id: crisisId,
        simulation: {
          crisis_id: crisisId,
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
          crisis_id: crisisId,
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
            setEpicenter={handleEpicenterChange}
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
            simulationResult={simulationResult}
            epicenter={epicenter}
            simulationLoading={simulationLoading}
            simulationError={simulationError}
          />
          </div>
        </div>

        {/* Right: Success Twin & Memo */}
        <div className="w-[30%] bg-[#0f1421] border-l border-gray-800 overflow-y-auto shrink-0 flex flex-col">
          <div className="flex-1 overflow-y-auto min-h-0">
          <SuccessTwinPanel
            key={epicenter}
            crises={crises}
            epicenter={epicenter}
            crisisProject={crisisProject}
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