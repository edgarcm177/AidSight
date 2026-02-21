import { ArrowUp, ArrowDown } from 'lucide-react';

interface ImpactPanelProps {
  scenarioRun: boolean;
  healthFunding: number;
  washFunding: number;
  inflationShock: number;
  droughtShock: boolean;
  conflictIntensity: number;
}

export function ImpactPanel({
  scenarioRun,
  healthFunding,
  washFunding,
  inflationShock,
  droughtShock,
  conflictIntensity,
}: ImpactPanelProps) {
  // Calculate scenario impact based on inputs
  const baselineTTC = 45;
  const scenarioTTC = scenarioRun
    ? Math.round(
        baselineTTC +
          (healthFunding / 1000000) * 2 +
          (washFunding / 1000000) * 1.5 -
          inflationShock * 0.5 -
          (droughtShock ? 8 : 0) -
          conflictIntensity * 15
      )
    : baselineTTC;

  const ttcChange = scenarioTTC - baselineTTC;
  const equityShift = scenarioRun
    ? Math.round(
        ((healthFunding + washFunding) / 10000000) * 8 -
          inflationShock * 0.3 -
          (droughtShock ? 5 : 0)
      )
    : 0;

  const regionsData = scenarioRun
    ? [
        { region: 'Banadir', deltaTTC: -12, fundingGap: 2.4 },
        { region: 'Bay & Bakool', deltaTTC: ttcChange > 0 ? 8 : -5, fundingGap: 1.8 },
        { region: 'Gedo', deltaTTC: droughtShock ? -15 : 3, fundingGap: 3.1 },
        { region: 'Lower Shabelle', deltaTTC: ttcChange > 0 ? 6 : -8, fundingGap: 2.2 },
      ]
    : [
        { region: 'Banadir', deltaTTC: 0, fundingGap: 0 },
        { region: 'Bay & Bakool', deltaTTC: 0, fundingGap: 0 },
        { region: 'Gedo', deltaTTC: 0, fundingGap: 0 },
        { region: 'Lower Shabelle', deltaTTC: 0, fundingGap: 0 },
      ];

  return (
    <div className="p-6">
      <h1 className="text-lg mb-6 tracking-tight text-gray-100">Impact & Fragility</h1>

      {/* Map Placeholder */}
      <div className="bg-[#0f1421] border border-gray-800 rounded-lg mb-6 h-64 flex items-center justify-center relative overflow-hidden">
        <div className="absolute inset-0 opacity-20">
          <svg className="w-full h-full" viewBox="0 0 400 250">
            {/* Abstract map representation */}
            <path
              d="M120,80 Q140,60 160,80 L180,100 Q190,110 185,125 L175,150 Q165,165 150,160 L130,155 Q115,150 110,135 Z"
              fill="#1e3a5f"
              stroke="#2d5a7f"
              strokeWidth="1"
            />
            <path
              d="M190,75 L215,85 Q230,90 235,105 L240,130 Q238,145 225,150 L205,155 Q190,152 185,140 L180,115 Z"
              fill="#2d3e50"
              stroke="#3d5e70"
              strokeWidth="1"
            />
            <path
              d="M150,165 L170,170 Q180,175 182,190 L180,215 Q175,230 160,232 L140,230 Q125,225 122,210 L120,185 Q122,170 135,167 Z"
              fill="#4a2d3e"
              stroke="#6a4d5e"
              strokeWidth="1"
            />
            <circle cx="145" cy="120" r="4" fill="#ef4444" opacity="0.8" />
            <circle cx="210" cy="115" r="3" fill="#f59e0b" opacity="0.7" />
            <circle cx="165" cy="195" r="5" fill="#dc2626" opacity="0.9" />
          </svg>
        </div>
        <div className="relative z-10 text-center">
          <div className="text-gray-500 text-sm mb-1">Fragility & Funding Map</div>
          <div className="text-xs text-gray-600">Regional vulnerability heatmap</div>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {/* Baseline TTC */}
        <div className="bg-[#0f1421] border border-gray-800 rounded-lg p-4">
          <div className="text-xs text-gray-500 mb-2 uppercase tracking-wider">
            Time to Collapse (baseline)
          </div>
          <div className="text-3xl text-gray-100 font-mono">{baselineTTC}</div>
          <div className="text-xs text-gray-600 mt-1">days</div>
        </div>

        {/* Scenario TTC */}
        <div className="bg-[#0f1421] border border-gray-800 rounded-lg p-4">
          <div className="text-xs text-gray-500 mb-2 uppercase tracking-wider">
            Time to Collapse (scenario)
          </div>
          <div className="flex items-center gap-2">
            <div className="text-3xl text-gray-100 font-mono">{scenarioTTC}</div>
            {scenarioRun && ttcChange !== 0 && (
              <div
                className={`flex items-center ${
                  ttcChange > 0 ? 'text-green-500' : 'text-red-500'
                }`}
              >
                {ttcChange > 0 ? (
                  <ArrowUp className="w-4 h-4" />
                ) : (
                  <ArrowDown className="w-4 h-4" />
                )}
                <span className="text-sm font-mono">{Math.abs(ttcChange)}</span>
              </div>
            )}
          </div>
          <div className="text-xs text-gray-600 mt-1">days</div>
        </div>

        {/* Equity Shift */}
        <div className="bg-[#0f1421] border border-gray-800 rounded-lg p-4">
          <div className="text-xs text-gray-500 mb-2 uppercase tracking-wider">
            Equity Shift (scenario)
          </div>
          <div
            className={`text-3xl font-mono ${
              equityShift > 0
                ? 'text-green-500'
                : equityShift < 0
                ? 'text-red-500'
                : 'text-gray-100'
            }`}
          >
            {equityShift > 0 ? '+' : ''}
            {equityShift}%
          </div>
          <div className="text-xs text-gray-600 mt-1">to high-need regions</div>
        </div>
      </div>

      {/* Regions Table */}
      <div className="bg-[#0f1421] border border-gray-800 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-800">
          <h3 className="text-sm text-gray-300">Regions Most Impacted</h3>
        </div>
        <table className="w-full">
          <thead>
            <tr className="bg-[#0a0e1a] border-b border-gray-800">
              <th className="text-left px-4 py-3 text-xs uppercase tracking-wider text-gray-500">
                Region
              </th>
              <th className="text-right px-4 py-3 text-xs uppercase tracking-wider text-gray-500">
                Δ TTC (days)
              </th>
              <th className="text-right px-4 py-3 text-xs uppercase tracking-wider text-gray-500">
                Funding gap (USD)
              </th>
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
                    row.deltaTTC > 0
                      ? 'text-green-500'
                      : row.deltaTTC < 0
                      ? 'text-red-500'
                      : 'text-gray-500'
                  }`}
                >
                  {row.deltaTTC > 0 ? '+' : ''}
                  {row.deltaTTC}
                </td>
                <td className="px-4 py-3 text-sm text-right font-mono text-amber-400">
                  ${row.fundingGap.toFixed(1)}M
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
