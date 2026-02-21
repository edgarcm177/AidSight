'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  api,
  type Project,
  type RegionMetric,
  type ScenarioParams,
  type ScenarioResult,
} from '@/lib/api';
import ChoroplethMap from '@/components/ChoroplethMap';
import RegionTable from '@/components/RegionTable';
import RegionDrawer from '@/components/RegionDrawer';
import ScenarioSliders from '@/components/ScenarioSliders';

export default function SandboxPage() {
  const [regions, setRegions] = useState<RegionMetric[]>([]);
  const [geojson, setGeojson] = useState<GeoJSON.FeatureCollection | null>(null);
  const [params, setParams] = useState<ScenarioParams>({
    inflation_shock: 0,
    climate_shock: 0,
    access_shock: 0,
    funding_delta: 0,
  });
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [drawerRegion, setDrawerRegion] = useState<RegionMetric | null>(null);
  const [drawerProjects, setDrawerProjects] = useState<Project[]>([]);

  const displayRegions = result?.updated_region_metrics ?? regions;

  const loadRegions = useCallback(async () => {
    try {
      const data = await api.regions();
      setRegions(data);
    } catch (e) {
      console.error('Failed to load regions', e);
    }
  }, []);

  const loadGeojson = useCallback(async () => {
    try {
      const res = await fetch('/geo/countries.geojson');
      const data = await res.json();
      setGeojson(data);
    } catch (e) {
      console.error('Failed to load GeoJSON', e);
    }
  }, []);

  useEffect(() => {
    loadRegions();
    loadGeojson();
  }, [loadRegions, loadGeojson]);

  const runStressTest = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.runScenario(params);
      setResult(r);
    } catch (e) {
      console.error('Scenario failed', e);
    } finally {
      setLoading(false);
    }
  }, [params]);

  const openDrawer = useCallback(async (regionId: string) => {
    try {
      const { region, projects } = await api.region(regionId);
      setDrawerRegion(region);
      setDrawerProjects(projects);
    } catch (e) {
      console.error('Failed to load region', e);
    }
  }, []);

  const totalGap = displayRegions.reduce((s, r) => s + r.funding_gap, 0);
  const totalReq = displayRegions.reduce(
    (s, r) => s + (r.required_funding ?? r.funding_gap + (r.funding_received ?? 0)),
    0
  );
  const weightedCoverage =
    totalReq > 0
      ? displayRegions.reduce(
          (s, r) => {
            const req = r.required_funding ?? 1;
            const cov = r.coverage_pct_stressed ?? r.coverage_pct;
            return s + cov * (req / totalReq);
          },
          0
        )
      : 0;
  const runways = displayRegions.map(
    (r) => r.runway_months_stressed ?? r.runway_months
  );
  const p10Runway =
    runways.length > 0
      ? runways.sort((a, b) => a - b)[Math.floor(runways.length * 0.1)] ?? 0
      : 0;

  return (
    <div className="mx-auto max-w-7xl space-y-4 p-4">
      <h1 className="text-2xl font-bold text-amber-400">
        AidSight Sandbox
      </h1>

      {/* KPI cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-lg border border-slate-700 bg-slate-900/50 p-4">
          <div className="text-sm text-slate-400">Total Gap</div>
          <div className="text-xl font-bold">
            ${(totalGap / 1e6).toFixed(0)}M
          </div>
        </div>
        <div className="rounded-lg border border-slate-700 bg-slate-900/50 p-4">
          <div className="text-sm text-slate-400">Portfolio Coverage</div>
          <div className="text-xl font-bold">
            {(weightedCoverage * 100).toFixed(0)}%
          </div>
        </div>
        <div className="rounded-lg border border-slate-700 bg-slate-900/50 p-4">
          <div className="text-sm text-slate-400">P10 Runway</div>
          <div className="text-xl font-bold">{p10Runway.toFixed(1)} mo</div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Map */}
        <div className="lg:col-span-2">
          <div className="rounded-lg border border-slate-700 bg-slate-900/30 p-2">
            <ChoroplethMap
              geojson={geojson}
              regionMetrics={displayRegions}
              onRegionClick={openDrawer}
            />
          </div>
        </div>

        {/* Sliders */}
        <div>
          <ScenarioSliders
            params={params}
            onChange={setParams}
            onRun={runStressTest}
            loading={loading}
          />
          {result && (
            <div className="mt-4 rounded-lg border border-slate-700 bg-slate-900/50 p-4">
              <h3 className="font-semibold text-amber-400">Suggested Allocation</h3>
              <ul className="mt-2 space-y-1 text-sm">
                {result.suggested_allocations.slice(0, 5).map((a) => (
                  <li key={a.region_id}>
                    {a.region_id}: +${(a.delta_funding / 1e6).toFixed(2)}M
                  </li>
                ))}
              </ul>
              <div className="mt-2 text-xs text-slate-400">
                Regret score: {result.regret_score.toFixed(3)}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Table */}
      <div>
        <h2 className="mb-2 text-lg font-semibold">Regions (click to drill down)</h2>
        <RegionTable regions={displayRegions} onRowClick={openDrawer} />
      </div>

      <RegionDrawer
        region={drawerRegion}
        projects={drawerProjects}
        onClose={() => setDrawerRegion(null)}
      />
    </div>
  );
}
