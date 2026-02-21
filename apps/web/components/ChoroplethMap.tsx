'use client';

import { useMemo } from 'react';
import dynamic from 'next/dynamic';
import type { GeoJsonObject } from 'geojson';

const MapContainer = dynamic(
  () => import('react-leaflet').then((m) => m.MapContainer),
  { ssr: false }
);
const TileLayer = dynamic(
  () => import('react-leaflet').then((m) => m.TileLayer),
  { ssr: false }
);
const GeoJSON = dynamic(
  () => import('react-leaflet').then((m) => m.GeoJSON),
  { ssr: false }
);

const PALETTE = ['#22c55e', '#84cc16', '#eab308', '#f97316', '#ef4444'];

function quantileBins(values: number[], n: number): number[] {
  const sorted = [...values].sort((a, b) => a - b);
  const bins: number[] = [];
  for (let i = 1; i < n; i++) {
    const idx = Math.floor((i / n) * sorted.length);
    bins.push(sorted[idx] ?? 0);
  }
  return bins;
}

function getColor(riskScore: number, bins: number[]): string {
  for (let i = 0; i < bins.length; i++) {
    if (riskScore <= bins[i]) return PALETTE[i];
  }
  return PALETTE[PALETTE.length - 1];
}

interface ChoroplethMapProps {
  geojson: GeoJsonObject | null;
  regionMetrics: { region_id: string; risk_score: number }[];
  onRegionClick?: (regionId: string) => void;
}

export default function ChoroplethMap({
  geojson,
  regionMetrics,
  onRegionClick,
}: ChoroplethMapProps) {
  const riskMap = useMemo(
    () => new Map(regionMetrics.map((r) => [r.region_id, r.risk_score])),
    [regionMetrics]
  );
  const bins = useMemo(
    () => quantileBins(regionMetrics.map((r) => r.risk_score), 5),
    [regionMetrics]
  );

  const style = (feature?: { properties?: { region_id?: string } }) => {
    const rid = feature?.properties?.region_id;
    const risk = rid ? riskMap.get(rid) ?? 0.5 : 0.5;
    return {
      fillColor: getColor(risk, bins),
      weight: 1,
      opacity: 1,
      color: '#334155',
      fillOpacity: 0.75,
    };
  };

  const onEach = (feature: { properties?: { region_id?: string } }, layer: L.Layer) => {
    const rid = feature?.properties?.region_id;
    if (rid && onRegionClick) {
      layer.on({ click: () => onRegionClick(rid) });
    }
  };

  if (!geojson) return null;

  return (
    <div className="h-full min-h-[400px] w-full rounded-lg overflow-hidden">
      <MapContainer
        center={[15, 40]}
        zoom={2}
        className="h-full w-full"
        zoomControl={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <GeoJSON data={geojson} style={style} onEachFeature={onEach} />
      </MapContainer>
    </div>
  );
}
