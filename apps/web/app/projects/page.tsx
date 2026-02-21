'use client';

import { useCallback, useEffect, useState } from 'react';
import { api, type Project } from '@/lib/api';

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [regionId, setRegionId] = useState<string>('');
  const [flagged, setFlagged] = useState<boolean | undefined>(undefined);

  const load = useCallback(async () => {
    try {
      const data = await api.projects({
        region_id: regionId || undefined,
        flagged,
      });
      setProjects(data);
    } catch (e) {
      console.error('Failed to load projects', e);
    }
  }, [regionId, flagged]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="mx-auto max-w-7xl space-y-4 p-4">
      <h1 className="text-2xl font-bold text-amber-400">Projects</h1>

      <div className="flex flex-wrap gap-4 rounded-lg border border-slate-700 bg-slate-900/50 p-4">
        <div>
          <label className="mr-2 text-sm text-slate-400">Region</label>
          <input
            type="text"
            placeholder="e.g. R1"
            value={regionId}
            onChange={(e) => setRegionId(e.target.value)}
            className="rounded border border-slate-600 bg-slate-800 px-2 py-1 text-sm"
          />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm text-slate-400">Flagged</label>
          <select
            value={flagged === undefined ? '' : String(flagged)}
            onChange={(e) =>
              setFlagged(
                e.target.value === ''
                  ? undefined
                  : e.target.value === 'true'
              )
            }
            className="rounded border border-slate-600 bg-slate-800 px-2 py-1 text-sm"
          >
            <option value="">All</option>
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-700">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-800/80">
            <tr>
              <th className="px-4 py-3 text-left font-medium">Title</th>
              <th className="px-4 py-3 text-left font-medium">Region</th>
              <th className="px-4 py-3 text-left font-medium">Sector</th>
              <th className="px-4 py-3 text-right font-medium">Budget</th>
              <th className="px-4 py-3 text-right font-medium">Beneficiaries</th>
            </tr>
          </thead>
          <tbody>
            {projects.map((p) => (
              <tr
                key={p.project_id}
                className="border-t border-slate-700/50 hover:bg-slate-800/50"
              >
                <td className="px-4 py-2">
                  <a
                    href={`/projects/${p.project_id}`}
                    className="font-medium text-amber-400 hover:underline"
                  >
                    {p.title}
                  </a>
                </td>
                <td className="px-4 py-2">{p.region_id}</td>
                <td className="px-4 py-2">{p.sector}</td>
                <td className="px-4 py-2 text-right">
                  ${(p.budget / 1e6).toFixed(2)}M
                </td>
                <td className="px-4 py-2 text-right">
                  {p.beneficiaries.toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
