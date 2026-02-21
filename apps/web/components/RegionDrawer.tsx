'use client';

import type { RegionMetric, Project } from '@/lib/api';

export default function RegionDrawer({
  region,
  projects,
  onClose,
}: {
  region: RegionMetric | null;
  projects: Project[];
  onClose: () => void;
}) {
  if (!region) return null;
  const cov = region.coverage_pct_stressed ?? region.coverage_pct;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/50" onClick={onClose}>
      <div
        className="w-full max-w-md overflow-y-auto bg-slate-900 border-l border-slate-700 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-700 p-4">
          <h2 className="text-lg font-semibold">{region.region_name}</h2>
          <button
            onClick={onClose}
            className="rounded p-2 text-slate-400 hover:bg-slate-800 hover:text-white"
          >
            ✕
          </button>
        </div>
        <div className="space-y-4 p-4">
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="rounded bg-slate-800/50 p-2">
              <span className="text-slate-400">Risk</span>
              <div className="font-medium">{(region.risk_score * 100).toFixed(0)}%</div>
            </div>
            <div className="rounded bg-slate-800/50 p-2">
              <span className="text-slate-400">Coverage</span>
              <div className="font-medium">{(cov * 100).toFixed(0)}%</div>
            </div>
            <div className="rounded bg-slate-800/50 p-2">
              <span className="text-slate-400">Funding Gap</span>
              <div className="font-medium">${(region.funding_gap / 1e6).toFixed(1)}M</div>
            </div>
            <div className="rounded bg-slate-800/50 p-2">
              <span className="text-slate-400">Runway</span>
              <div className="font-medium">
                {(region.runway_months_stressed ?? region.runway_months).toFixed(1)} mo
              </div>
            </div>
          </div>
          <div>
            <h3 className="mb-2 font-medium text-slate-300">Projects</h3>
            <ul className="space-y-2">
              {projects.map((p) => (
                <li
                  key={p.project_id}
                  className="rounded border border-slate-700/50 bg-slate-800/30 p-2"
                >
                  <a
                    href={`/projects/${p.project_id}`}
                    className="font-medium text-amber-400 hover:underline"
                  >
                    {p.title}
                  </a>
                  <div className="mt-1 text-xs text-slate-400">
                    {p.sector} · ${(p.budget / 1e6).toFixed(2)}M · {p.beneficiaries.toLocaleString()} beneficiaries
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
