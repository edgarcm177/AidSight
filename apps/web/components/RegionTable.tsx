'use client';

import { useState } from 'react';
import type { RegionMetric } from '@/lib/api';

type SortKey = keyof Pick<
  RegionMetric,
  'region_name' | 'risk_score' | 'coverage_pct' | 'funding_gap' | 'runway_months'
>;

export default function RegionTable({
  regions,
  onRowClick,
}: {
  regions: RegionMetric[];
  onRowClick?: (regionId: string) => void;
}) {
  const [sortKey, setSortKey] = useState<SortKey>('risk_score');
  const [asc, setAsc] = useState(false);

  const sorted = [...regions].sort((a, b) => {
    const av = a[sortKey] ?? 0;
    const bv = b[sortKey] ?? 0;
    if (typeof av === 'string' && typeof bv === 'string')
      return asc ? av.localeCompare(bv) : bv.localeCompare(av);
    return asc ? (av as number) - (bv as number) : (bv as number) - (av as number);
  });

  const toggle = (k: SortKey) => {
    setSortKey(k);
    setAsc((a) => !a);
  };

  const cov = (r: RegionMetric) =>
    r.coverage_pct_stressed ?? r.coverage_pct;

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-700">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-800/80">
          <tr>
            <th
              className="cursor-pointer px-4 py-3 text-left font-medium hover:bg-slate-700/50"
              onClick={() => toggle('region_name')}
            >
              Region {sortKey === 'region_name' && (asc ? '↑' : '↓')}
            </th>
            <th
              className="cursor-pointer px-4 py-3 text-right font-medium hover:bg-slate-700/50"
              onClick={() => toggle('risk_score')}
            >
              Risk {sortKey === 'risk_score' && (asc ? '↑' : '↓')}
            </th>
            <th
              className="cursor-pointer px-4 py-3 text-right font-medium hover:bg-slate-700/50"
              onClick={() => toggle('coverage_pct')}
            >
              Coverage {sortKey === 'coverage_pct' && (asc ? '↑' : '↓')}
            </th>
            <th
              className="cursor-pointer px-4 py-3 text-right font-medium hover:bg-slate-700/50"
              onClick={() => toggle('funding_gap')}
            >
              Gap (M) {sortKey === 'funding_gap' && (asc ? '↑' : '↓')}
            </th>
            <th
              className="cursor-pointer px-4 py-3 text-right font-medium hover:bg-slate-700/50"
              onClick={() => toggle('runway_months')}
            >
              Runway {sortKey === 'runway_months' && (asc ? '↑' : '↓')}
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <tr
              key={r.region_id}
              className="cursor-pointer border-t border-slate-700/50 hover:bg-slate-800/50"
              onClick={() => onRowClick?.(r.region_id)}
            >
              <td className="px-4 py-2 font-medium">{r.region_name}</td>
              <td className="px-4 py-2 text-right">
                <span
                  className={
                    r.risk_score > 0.75
                      ? 'text-red-400'
                      : r.risk_score > 0.5
                        ? 'text-amber-400'
                        : 'text-emerald-400'
                  }
                >
                  {(r.risk_score * 100).toFixed(0)}%
                </span>
              </td>
              <td className="px-4 py-2 text-right">
                {(cov(r) * 100).toFixed(0)}%
              </td>
              <td className="px-4 py-2 text-right">
                {(r.funding_gap / 1e6).toFixed(1)}
              </td>
              <td className="px-4 py-2 text-right">
                {r.runway_months_stressed ?? r.runway_months} mo
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
