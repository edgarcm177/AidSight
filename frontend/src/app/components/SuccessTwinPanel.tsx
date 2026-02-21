import { ExternalLink } from 'lucide-react';
import type { TwinResult, MemoResponse } from '../../lib/api';

interface SuccessTwinPanelProps {
  twinResult: TwinResult | null;
  twinLoading: boolean;
  twinError: string | null;
  onFindTwin: () => void;
  memoResult: MemoResponse | null;
  memoLoading: boolean;
  memoError: string | null;
  onGenerateMemo: () => void;
  canGenerateMemo: boolean;
}

export function SuccessTwinPanel({
  twinResult,
  twinLoading,
  twinError,
  onFindTwin,
  memoResult,
  memoLoading,
  memoError,
  onGenerateMemo,
  canGenerateMemo,
}: SuccessTwinPanelProps) {
  return (
    <div className="p-6 flex flex-col h-full">
      {/* Success Twin Card */}
      <div className="bg-[#0a0e1a] border border-gray-800 rounded-lg p-5 mb-6">
        <h2 className="text-sm uppercase tracking-wider text-gray-500 mb-4">Success Twin</h2>

        {twinResult ? (
          <>
            <h3 className="text-base text-teal-400 mb-3">
              Twin: {twinResult.twin_project_id}
            </h3>
            <div className="mb-4">
              <span className="text-xs text-gray-500">Similarity: </span>
              <span className="text-sm font-mono text-teal-400">
                {(twinResult.similarity_score * 100).toFixed(1)}%
              </span>
            </div>
            <ul className="space-y-2 mb-4">
              {twinResult.bullets.map((b, i) => (
                <li key={i} className="text-sm text-gray-300 flex items-start">
                  <span className="text-teal-500 mr-2">•</span>
                  <span>{b}</span>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <div className="text-sm text-gray-500 mb-4">
            Click to find a Success Twin for sample project PRJ001.
          </div>
        )}

        {twinError && (
          <div className="mb-4 p-2 bg-red-900/30 border border-red-700 rounded text-xs text-red-300">
            {twinError}
          </div>
        )}

        <button
          onClick={onFindTwin}
          disabled={twinLoading}
          className="flex items-center gap-1.5 text-sm text-teal-400 hover:text-teal-300 disabled:opacity-50 transition-colors"
        >
          {twinLoading ? 'Loading...' : (
            <>
              <span>Find Success Twin</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </>
          )}
        </button>
      </div>

      {/* Contrarian Decision Memo */}
      <div className="bg-[#0a0e1a] border border-gray-800 rounded-lg flex-1 flex flex-col overflow-hidden min-h-[200px]">
        <div className="px-5 py-4 border-b border-gray-800">
          <h2 className="text-sm uppercase tracking-wider text-gray-500 mb-1">Contrarian Decision Memo</h2>
          <div className="text-xs text-gray-600">AI Analyst Feedback</div>
        </div>

        {memoResult ? (
          <>
            <div className="px-5 py-3 border-b border-gray-800">
              <h3 className="text-base text-gray-200 font-medium">{memoResult.title}</h3>
            </div>
            <div className="px-5 py-3 border-b border-gray-800 flex flex-wrap gap-2">
              {memoResult.key_risks.map((tag) => (
                <span
                  key={tag}
                  className="px-2.5 py-1 bg-[#1a1f2e] border border-gray-700 rounded-full text-xs text-amber-400"
                >
                  {tag}
                </span>
              ))}
            </div>
            <div className="flex-1 overflow-y-auto px-5 py-4">
              <div className="text-sm text-gray-400 leading-relaxed whitespace-pre-line">
                {memoResult.body}
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 overflow-y-auto px-5 py-4">
            <div className="text-sm text-gray-500 mb-4">
              Run a scenario first, then generate the memo.
            </div>
            {memoError && (
              <div className="mb-4 p-2 bg-red-900/30 border border-red-700 rounded text-xs text-red-300">
                {memoError}
              </div>
            )}
          </div>
        )}

        <div className="px-5 py-4 border-t border-gray-800 shrink-0">
          <button
            onClick={onGenerateMemo}
            disabled={!canGenerateMemo || memoLoading}
            className="w-full py-2 rounded text-sm font-medium bg-teal-600 hover:bg-teal-500 disabled:opacity-50 disabled:cursor-not-allowed text-white transition-colors"
          >
            {memoLoading ? 'Generating...' : 'Generate Memo'}
          </button>
        </div>
      </div>
    </div>
  );
}
