import { ArrowUp, ArrowDown } from 'lucide-react';
import type { Crisis, SimulationResult } from '../../lib/api';

interface ImpactPanelProps {
  selectedCrisis: Crisis | undefined;
  simulationResult: SimulationResult | null;
  simulationLoading: boolean;
}

export function ImpactPanel({
  selectedCrisis,
  simulationResult,
  simulationLoading,
}: ImpactPanelProps) {
  const baselineTTC = simulationResult?.metrics.baseline_ttc_days ?? (selectedCrisis
    ? Math.max(1, (selectedCrisis.coverage * 180) / Math.max(1, selectedCrisis.severity))
    : null);
  const scenarioTTC = simulationResult?.metrics.scenario_ttc_days ?? null;
  const ttcChange = scenarioTTC != null && baselineTTC != null ? scenarioTTC - baselineTTC : null;
  const equityShift = simulationResult?.metrics.scenario_equity_shift_pct ?? null;
  const regionsData = simulationResult?.impacted_regions ?? [];

  const hasScenario = !!simulationResult;

  return (
    <div className="p-6">
      {/* Selected crisis summary */}
      {selectedCrisis && (
        <div className="mb-6 p-4 bg-[#0f1421] border border-gray-800 rounded-lg">
          <h3 className="text-sm text-gray-500 mb-2">Selected crisis</h3>
          <div className="text-gray-200 font-medium">{selectedCrisis.name}</div>
          <div className="text-xs text-gray-500 mt-1">
            {selectedCrisis.country} · {selectedCrisis.year} · Severity {selectedCrisis.severity.toFixed(1)} ·
            Coverage {(selectedCrisis.coverage * 100).toFixed(1)}%
          </div>
        </div>
      )}

      {/* Map Placeholder */}
      <div className="bg-[#0f1421] border border-gray-800 rounded-lg mb-6 h-40 flex items-center justify-center relative overflow-hidden">
        <div className="relative z-10 text-center">
          <div className="text-gray-500 text-sm mb-1">Fragility & Funding Map</div>
          <div className="text-xs text-gray-600">Regional vulnerability heatmap</div>
        </div>
      </div>

      {/* Metric Cards */}
      {!hasScenario && !simulationLoading ? (
        <div className="mb-6 p-6 bg-[#0f1421] border border-gray-800 rounded-lg text-center">
          <p className="text-sm text-gray-500">Run a scenario to see impact.</p>
          <p className="text-xs text-gray-600 mt-2">Select a crisis and click Run Scenario.</p>
        </div>
      ) : (
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-[#0f1421] border border-gray-800 rounded-lg p-4">
          <div className="text-xs text-gray-500 mb-2 uppercase tracking-wider">Time to Collapse (baseline)</div>
          <div className="text-2xl text-gray-100 font-mono">
            {baselineTTC != null ? `${baselineTTC.toFixed(1)} days` : '—'}
          </div>
        </div>

        <div className="bg-[#0f1421] border border-gray-800 rounded-lg p-4">
          <div className="text-xs text-gray-500 mb-2 uppercase tracking-wider">Time to Collapse (scenario)</div>
          <div className="flex items-center gap-2 flex-wrap">
            <div className="text-2xl text-gray-100 font-mono">
              {simulationLoading ? '…' : scenarioTTC != null ? `${scenarioTTC.toFixed(1)} days` : '—'}
            </div>
            {ttcChange != null && ttcChange !== 0 && (
              <span className={`flex items-center text-sm font-mono ${ttcChange > 0 ? 'text-green-500' : 'text-red-500'}`}>
                {ttcChange > 0 ? <ArrowUp className="w-4 h-4 mr-0.5" /> : <ArrowDown className="w-4 h-4 mr-0.5" />}
                {ttcChange > 0 ? '+' : ''}{ttcChange.toFixed(0)} days
              </span>
            )}
          </div>
        </div>

        <div className="bg-[#0f1421] border border-gray-800 rounded-lg p-4">
          <div className="text-xs text-gray-500 mb-2 uppercase tracking-wider">
            Equity Shift
            <span className="ml-1.5 text-gray-600 font-normal" title="Positive = more equitable coverage, negative = less equitable.">ⓘ</span>
          </div>
          <div
            className={`text-2xl font-mono ${
              equityShift != null
                ? equityShift > 0
                  ? 'text-green-500'
                  : equityShift < 0
                    ? 'text-red-500'
                    : 'text-gray-100'
                : 'text-gray-100'
            }`}
            title="Positive = more equitable coverage, negative = less equitable."
          >
            {equityShift != null ? (equityShift > 0 ? '+' : '') + equityShift.toFixed(1) + ' pts' : '—'}
          </div>
        </div>
      </div>
      )}

      {/* Regions Table */}
      <div className="bg-[#0f1421] border border-gray-800 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-800">
          <h3 className="text-sm text-gray-300">Regions Most Impacted</h3>
          <p className="text-xs text-gray-600 mt-0.5">Δ TTC and funding gap by region</p>
        </div>
        {regionsData.length > 0 ? (
          <table className="w-full">
            <thead>
              <tr className="bg-[#0a0e1a] border-b border-gray-800">
                <th className="text-left px-4 py-3 text-xs uppercase tracking-wider text-gray-500">Region</th>
                <th className="text-right px-4 py-3 text-xs uppercase tracking-wider text-gray-500">Δ TTC (days)</th>
                <th className="text-right px-4 py-3 text-xs uppercase tracking-wider text-gray-500">Funding gap (USD)</th>
              </tr>
            </thead>
            <tbody>
              {regionsData.map((row, index) => (
                <tr
                  key={row.region}
                  className={index < regionsData.length - 1 ? 'border-b border-gray-800' : ''}
                >
                  <td className="px-4 py-3 text-sm text-gray-300">{row.region}</td>
                  <td
                    className={`px-4 py-3 text-sm text-right font-mono ${
                      row.delta_ttc_days > 0
                        ? 'text-green-500'
                        : row.delta_ttc_days < 0
                          ? 'text-red-500'
                          : 'text-gray-500'
                    }`}
                  >
                    {row.delta_ttc_days > 0 ? '+' : ''}
                    {row.delta_ttc_days.toFixed(0)}
                  </td>
                  <td className="px-4 py-3 text-sm text-right font-mono text-amber-400">
                    ${(row.funding_gap_usd / 1_000_000).toFixed(2)}M
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="px-4 py-8 text-sm text-gray-500 text-center">
            <p>No impacted regions yet.</p>
            <p className="text-xs mt-1">Run a scenario to see regional impact.</p>
          </div>
        )}
      </div>
    </div>
  );
}
