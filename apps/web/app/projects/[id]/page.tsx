'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import {
  api,
  type Project,
  type ComparableTrade,
  type Memo,
  type MemoContext,
  type ScenarioParams,
} from '@/lib/api';

export default function ProjectDetailPage() {
  const params = useParams();
  const id = params?.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [comparables, setComparables] = useState<ComparableTrade[]>([]);
  const [memo, setMemo] = useState<Memo | null>(null);
  const [loadingComp, setLoadingComp] = useState(false);
  const [loadingMemo, setLoadingMemo] = useState(false);
  const [memoOpen, setMemoOpen] = useState<string | null>('recommendation');

  const loadProject = useCallback(async () => {
    if (!id) return;
    try {
      const p = await api.project(id);
      setProject(p);
    } catch (e) {
      console.error('Failed to load project', e);
    }
  }, [id]);

  useEffect(() => {
    loadProject();
  }, [loadProject]);

  const fetchComparables = useCallback(async () => {
    if (!id) return;
    setLoadingComp(true);
    try {
      const c = await api.comparables(id);
      setComparables(c);
    } catch (e) {
      console.error('Failed to load comparables', e);
    } finally {
      setLoadingComp(false);
    }
  }, [id]);

  const generateMemo = useCallback(async () => {
    if (!project) return;
    setLoadingMemo(true);
    try {
      const scenario: ScenarioParams = {
        inflation_shock: 0.1,
        climate_shock: 0.05,
        access_shock: 0.1,
        funding_delta: 0,
      };
      const ctx: MemoContext = {
        scenario_params: scenario,
        project,
        comparables,
      };
      const m = await api.generateMemo(ctx);
      setMemo(m);
      setMemoOpen('recommendation');
    } catch (e) {
      console.error('Failed to generate memo', e);
    } finally {
      setLoadingMemo(false);
    }
  }, [project, comparables]);

  if (!project) {
    return (
      <div className="mx-auto max-w-4xl p-4">
        <p className="text-slate-400">Loading...</p>
      </div>
    );
  }

  const sections = memo?.sections ?? {};
  const sectionKeys = [
    'recommendation',
    'base_case',
    'downside_case',
    'severe_case',
    'risks',
    'red_team',
    'evidence',
  ];

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-4">
      <a href="/projects" className="text-sm text-amber-400 hover:underline">
        ← Back to Projects
      </a>

      <div className="rounded-lg border border-slate-700 bg-slate-900/50 p-6">
        <h1 className="text-xl font-bold text-amber-400">{project.title}</h1>
        <div className="mt-2 flex flex-wrap gap-4 text-sm text-slate-400">
          <span>Region: {project.region_id}</span>
          <span>Sector: {project.sector}</span>
          <span>Budget: ${(project.budget / 1e6).toFixed(2)}M</span>
          <span>Beneficiaries: {project.beneficiaries.toLocaleString()}</span>
        </div>
        <p className="mt-4 text-slate-300">{project.description}</p>
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Comparable Trades</h2>
          <button
            onClick={fetchComparables}
            disabled={loadingComp}
            className="rounded bg-amber-500 px-4 py-2 text-sm font-medium text-slate-900 hover:bg-amber-400 disabled:opacity-50"
          >
            {loadingComp ? 'Loading…' : 'Find Comparable Trades'}
          </button>
        </div>
        {comparables.length > 0 && (
          <ul className="space-y-3">
            {comparables.map((c) => (
              <li
                key={c.project_id}
                className="rounded-lg border border-slate-700 bg-slate-900/50 p-4"
              >
                <a
                  href={`/projects/${c.project_id}`}
                  className="font-medium text-amber-400 hover:underline"
                >
                  {c.title}
                </a>
                <div className="mt-1 text-sm text-slate-400">
                  Similarity: {(c.similarity * 100).toFixed(0)}%
                </div>
                <ul className="mt-2 list-inside list-disc text-sm text-slate-300">
                  {c.key_reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-lg font-semibold">IC Memo + Red Team</h2>
          <button
            onClick={generateMemo}
            disabled={loadingMemo}
            className="rounded bg-amber-500 px-4 py-2 text-sm font-medium text-slate-900 hover:bg-amber-400 disabled:opacity-50"
          >
            {loadingMemo ? 'Generating…' : 'Generate IC Memo + Red Team'}
          </button>
        </div>
        {memo && (
          <div className="space-y-2">
            {sectionKeys.map((key) => (
              <div
                key={key}
                className="rounded-lg border border-slate-700 bg-slate-900/50 overflow-hidden"
              >
                <button
                  onClick={() =>
                    setMemoOpen((o) => (o === key ? null : key))
                  }
                  className="flex w-full items-center justify-between px-4 py-3 text-left font-medium"
                >
                  <span className="capitalize">{key.replace(/_/g, ' ')}</span>
                  <span>{memoOpen === key ? '−' : '+'}</span>
                </button>
                {memoOpen === key && sections[key] && (
                  <div className="border-t border-slate-700 px-4 py-3 text-sm text-slate-300">
                    {sections[key]}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
