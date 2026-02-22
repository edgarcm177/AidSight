/**
 * AidSight diagnostics - logs feature status to console so you (or AI) can verify
 * what's live vs hardcoded and whether fixes are working.
 *
 * Check DevTools Console for "[AidSight]" logs.
 */

export type DiagnosticStatus = 'LIVE' | 'HARDCODED' | 'PLACEHOLDER' | 'API_PENDING' | 'API_ERROR';

export interface AidSightDiagnostics {
  timestamp: string;
  impactCards: {
    source: DiagnosticStatus;
    simulationResult: boolean;
    epicenter?: string;
    totalDisplaced?: number;
    totalCost?: number;
    affectedCount?: number;
  };
  affectedCountries: {
    source: DiagnosticStatus;
    count: number;
    countries?: string[];
  };
  aiSummary: { source: DiagnosticStatus };
  map: {
    status: DiagnosticStatus;
    epicenterSent?: string;
    affectedSent?: string[];
    message: string;
  };
  successTwin: { source: DiagnosticStatus; projectId?: string };
  vectorNeighbors: { source: DiagnosticStatus; count?: number };
  memo: { source: DiagnosticStatus };
  sphinx: { source: DiagnosticStatus };
}

function logDiagnostics(d: AidSightDiagnostics) {
  const header = '%c[AidSight] Feature Status';
  console.groupCollapsed(header + ' — ' + d.timestamp, 'color: #14b8a6; font-weight: bold');
  console.table({
    'Impact cards': d.impactCards.source,
    'Affected countries': d.affectedCountries.source,
    'AI Summary': d.aiSummary.source,
    'Map': d.map.status + ': ' + d.map.message,
    'Success Twin': d.successTwin.source,
    'Vector neighbors': d.vectorNeighbors.source,
    'Memo': d.memo.source,
    'Sphinx': d.sphinx.source,
  });
  console.log('Details:', d);
  console.groupEnd();
}

export function reportDiagnostics(d: Partial<AidSightDiagnostics> & { timestamp?: string }) {
  const full: AidSightDiagnostics = {
    timestamp: d.timestamp ?? new Date().toISOString(),
    impactCards: d.impactCards ?? { source: 'PLACEHOLDER', simulationResult: false },
    affectedCountries: d.affectedCountries ?? { source: 'PLACEHOLDER', count: 0 },
    aiSummary: d.aiSummary ?? { source: 'PLACEHOLDER' },
    map: d.map ?? { status: 'PLACEHOLDER', message: 'No data sent' },
    successTwin: d.successTwin ?? { source: 'PLACEHOLDER' },
    vectorNeighbors: d.vectorNeighbors ?? { source: 'PLACEHOLDER' },
    memo: d.memo ?? { source: 'PLACEHOLDER' },
    sphinx: d.sphinx ?? { source: 'PLACEHOLDER' },
  };
  logDiagnostics(full);
}
