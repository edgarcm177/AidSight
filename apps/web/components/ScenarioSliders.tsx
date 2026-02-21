'use client';

import type { ScenarioParams } from '@/lib/api';

export default function ScenarioSliders({
  params,
  onChange,
  onRun,
  loading,
}: {
  params: ScenarioParams;
  onChange: (params: ScenarioParams) => void;
  onRun: () => void;
  loading?: boolean;
}) {
  return (
    <div className="space-y-4 rounded-lg border border-slate-700 bg-slate-900/50 p-4">
      <h3 className="font-semibold text-amber-400">Scenario Parameters</h3>
      <div className="space-y-3">
        <div>
          <label className="mb-1 block text-xs text-slate-400">
            Inflation shock ({Math.round(params.inflation_shock * 100)}%)
          </label>
          <input
            type="range"
            min={0}
            max={100}
            value={params.inflation_shock * 100}
            onChange={(e) =>
              onChange({ ...params, inflation_shock: Number(e.target.value) / 100 })
            }
            className="w-full accent-amber-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-400">
            Climate shock ({Math.round(params.climate_shock * 100)}%)
          </label>
          <input
            type="range"
            min={0}
            max={100}
            value={params.climate_shock * 100}
            onChange={(e) =>
              onChange({ ...params, climate_shock: Number(e.target.value) / 100 })
            }
            className="w-full accent-amber-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-400">
            Access shock ({Math.round(params.access_shock * 100)}%)
          </label>
          <input
            type="range"
            min={0}
            max={100}
            value={params.access_shock * 100}
            onChange={(e) =>
              onChange({ ...params, access_shock: Number(e.target.value) / 100 })
            }
            className="w-full accent-amber-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-400">
            Funding delta (${(params.funding_delta / 1e6).toFixed(1)}M)
          </label>
          <input
            type="range"
            min={-50}
            max={100}
            value={params.funding_delta / 1e6}
            onChange={(e) =>
              onChange({ ...params, funding_delta: Number(e.target.value) * 1e6 })
            }
            className="w-full accent-amber-500"
          />
        </div>
      </div>
      <button
        onClick={onRun}
        disabled={loading}
        className="w-full rounded bg-amber-500 px-4 py-2 font-medium text-slate-900 hover:bg-amber-400 disabled:opacity-50"
      >
        {loading ? 'Running…' : 'Run Stress Test'}
      </button>
    </div>
  );
}
