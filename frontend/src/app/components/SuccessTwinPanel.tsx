import { ExternalLink } from 'lucide-react';

interface SuccessTwinPanelProps {
  scenarioRun: boolean;
  inflationShock: number;
  droughtShock: boolean;
}

export function SuccessTwinPanel({
  scenarioRun,
  inflationShock,
  droughtShock,
}: SuccessTwinPanelProps) {
  const riskTags = scenarioRun
    ? [
        inflationShock > 10 ? 'Inflation risk' : null,
        droughtShock ? 'Climate shock' : null,
        'Coverage drop',
        'Unreached red zone',
        inflationShock > 20 ? 'Fuel price spike' : null,
      ].filter(Boolean)
    : ['Inflation risk', 'Coverage drop', 'Unreached red zone'];

  return (
    <div className="p-6 flex flex-col h-full">
      {/* Success Twin Card */}
      <div className="bg-[#0a0e1a] border border-gray-800 rounded-lg p-5 mb-6">
        <h2 className="text-sm uppercase tracking-wider text-gray-500 mb-4">Success Twin</h2>

        <h3 className="text-base text-teal-400 mb-3">
          Kenya Drought Health Response 2011
        </h3>

        <div className="space-y-2 mb-4">
          <div className="flex text-xs">
            <span className="text-gray-500 w-20">Country:</span>
            <span className="text-gray-300">Kenya</span>
          </div>
          <div className="flex text-xs">
            <span className="text-gray-500 w-20">Year:</span>
            <span className="text-gray-300">2011</span>
          </div>
          <div className="flex text-xs">
            <span className="text-gray-500 w-20">Sector:</span>
            <span className="text-gray-300">Health, Nutrition</span>
          </div>
        </div>

        <ul className="space-y-2 mb-4">
          <li className="text-sm text-gray-300 flex items-start">
            <span className="text-teal-500 mr-2">•</span>
            <span>Survived past inflation shock (18% peak)</span>
          </li>
          <li className="text-sm text-gray-300 flex items-start">
            <span className="text-teal-500 mr-2">•</span>
            <span>Used decentralized delivery model</span>
          </li>
          <li className="text-sm text-gray-300 flex items-start">
            <span className="text-teal-500 mr-2">•</span>
            <span>Maintained coverage during conflict escalation</span>
          </li>
        </ul>

        <button className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-teal-400 transition-colors">
          <span>View details</span>
          <ExternalLink className="w-3 h-3" />
        </button>
      </div>

      {/* Contrarian Decision Memo */}
      <div className="bg-[#0a0e1a] border border-gray-800 rounded-lg flex-1 flex flex-col overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-800">
          <h2 className="text-sm uppercase tracking-wider text-gray-500 mb-1">
            Contrarian Decision Memo
          </h2>
          <div className="text-xs text-gray-600">AI Analyst Feedback</div>
        </div>

        {/* Risk Tags */}
        <div className="px-5 py-3 border-b border-gray-800 flex flex-wrap gap-2">
          {riskTags.map((tag) => (
            <span
              key={tag}
              className="px-2.5 py-1 bg-[#1a1f2e] border border-gray-700 rounded-full text-xs text-amber-400"
            >
              {tag}
            </span>
          ))}
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          <div className="space-y-4 text-sm text-gray-400 leading-relaxed">
            <p>
              <span className="text-amber-400">Warning:</span> The scenario's{' '}
              {inflationShock}% inflation shock significantly erodes purchasing power. Based
              on historical data, health sector supply chains show 23% cost overruns at this
              inflation level. Time-to-collapse (TTC) may deteriorate faster than projected.
            </p>

            {droughtShock && (
              <p>
                The drought shock introduces compounding stress to WASH infrastructure. Water
                trucking costs typically double under drought conditions, creating a $1.2M–$2.8M
                additional gap not captured in baseline funding scenarios.
              </p>
            )}

            <p>
              <span className="text-teal-400">Opportunity:</span> Increased health and WASH
              funding creates buffer capacity. However, {scenarioRun ? 'the' : 'historical'}{' '}
              allocation pattern favors urban clusters (Banadir). Rural high-need regions like
              Gedo remain underfunded, risking equity regression.
            </p>

            <p>
              Conflict intensity at {scenarioRun ? (0.3).toFixed(1) : '0.3'} suggests moderate
              access constraints. Compare to Success Twin (Kenya 2011), which operated at 0.45
              conflict intensity but used mobile health units to bypass blockages. Consider
              similar deployment strategy.
            </p>

            <p>
              <span className="text-red-400">Blind spot:</span> The scenario does not test fuel
              price volatility or partner organization capacity constraints. Both factors were
              primary collapse triggers in Yemen 2022 and Ethiopia 2021. Recommend adding fuel
              price shock parameter.
            </p>

            {inflationShock > 15 && (
              <p>
                <span className="text-amber-400">Critical threshold:</span> Inflation above 15%
                historically correlates with NGO partner withdrawal. Monitor for cascade
                failures if scenario proceeds to implementation.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
