'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Loader2,
  AlertCircle,
  History,
  ChevronLeft,
  ChevronRight,
  FileText,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getAgentConfigHistory } from '@/lib/api/agent-config.api';

const changeTypeColors: Record<string, string> = {
  identity: 'bg-blue-100 text-blue-800',
  policy: 'bg-purple-100 text-purple-800',
  escalation: 'bg-amber-100 text-amber-800',
  integrations: 'bg-green-100 text-green-800',
};

const changeTypeLabels: Record<string, string> = {
  identity: 'Identity',
  policy: 'Policy',
  escalation: 'Escalation',
  integrations: 'Integrations',
};

function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

interface HistoryTabProps {
  agentId: string;
}

export default function HistoryTab({ agentId }: HistoryTabProps) {
  const [page, setPage] = useState(1);
  const [expandedEntry, setExpandedEntry] = useState<string | null>(null);

  const {
    data: historyData,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['agentConfigHistory', agentId, page],
    queryFn: () => getAgentConfigHistory(agentId, { page, pageSize: 15 }),
    enabled: !!agentId,
  });

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <Loader2 className="w-6 h-6 animate-spin text-primary-600" />
        <p className="text-sm text-gray-500 mt-3">Loading history...</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <AlertCircle className="w-6 h-6 text-red-500 mb-2" />
        <p className="text-sm text-gray-500">Failed to load config history.</p>
      </div>
    );
  }

  const entries = historyData?.entries || [];
  const meta = historyData?.meta;

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
      <div className="p-6 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <History className="w-5 h-5 text-primary-600" />
          <h2 className="text-base font-semibold text-gray-900">Configuration History</h2>
          {meta && (
            <span className="ml-1 px-2 py-0.5 rounded-full bg-gray-100 text-xs font-medium text-gray-600">
              {meta.totalItems} changes
            </span>
          )}
        </div>
        <p className="text-sm text-gray-500 mt-1">
          View a chronological log of all configuration changes made to this agent.
        </p>
      </div>

      <div className="p-6">
        {entries.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16">
            <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gray-100 mb-3">
              <History className="w-6 h-6 text-gray-400" />
            </div>
            <p className="text-sm font-medium text-gray-600">No configuration changes yet</p>
            <p className="text-xs text-gray-400 mt-1">
              Changes to the agent configuration will appear here.
            </p>
          </div>
        ) : (
          <div className="space-y-1">
            {/* Table Header */}
            <div className="grid grid-cols-12 gap-4 pb-3 border-b border-gray-100">
              <div className="col-span-1">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">#</p>
              </div>
              <div className="col-span-2">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Type</p>
              </div>
              <div className="col-span-4">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                  Summary
                </p>
              </div>
              <div className="col-span-2">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                  Changed By
                </p>
              </div>
              <div className="col-span-3">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Date</p>
              </div>
            </div>

            {/* Table Rows */}
            {entries.map((entry) => {
              const isExpanded = expandedEntry === entry.id;

              return (
                <div key={entry.id}>
                  <button
                    onClick={() => setExpandedEntry(isExpanded ? null : entry.id)}
                    className="w-full grid grid-cols-12 gap-4 py-3.5 border-b border-gray-50 last:border-0 items-center text-left hover:bg-gray-50 transition-colors rounded-lg px-1"
                  >
                    <div className="col-span-1">
                      <span className="text-xs font-mono text-gray-400">v{entry.version}</span>
                    </div>
                    <div className="col-span-2">
                      <span
                        className={cn(
                          'inline-block px-2 py-0.5 rounded-full text-xs font-medium',
                          changeTypeColors[entry.changeType] || 'bg-gray-100 text-gray-800',
                        )}
                      >
                        {changeTypeLabels[entry.changeType] || entry.changeType}
                      </span>
                    </div>
                    <div className="col-span-4">
                      <p className="text-sm text-gray-900 truncate">{entry.changeSummary}</p>
                    </div>
                    <div className="col-span-2">
                      <p className="text-sm text-gray-500 truncate">{entry.changedBy}</p>
                    </div>
                    <div className="col-span-3">
                      <p className="text-xs text-gray-500">{formatDateTime(entry.changedAt)}</p>
                    </div>
                  </button>

                  {/* Expanded Details */}
                  {isExpanded && (
                    <div className="mx-1 mb-3 p-4 rounded-lg bg-gray-50 border border-gray-200">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <div className="flex items-center gap-1.5 mb-2">
                            <FileText className="w-3.5 h-3.5 text-gray-400" />
                            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                              Previous Value
                            </p>
                          </div>
                          <pre className="text-xs text-gray-700 bg-white rounded-lg border border-gray-200 p-3 overflow-x-auto max-h-48 overflow-y-auto font-mono whitespace-pre-wrap break-words">
                            {entry.previousValue || '(empty)'}
                          </pre>
                        </div>
                        <div>
                          <div className="flex items-center gap-1.5 mb-2">
                            <FileText className="w-3.5 h-3.5 text-primary-500" />
                            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                              New Value
                            </p>
                          </div>
                          <pre className="text-xs text-gray-700 bg-white rounded-lg border border-gray-200 p-3 overflow-x-auto max-h-48 overflow-y-auto font-mono whitespace-pre-wrap break-words">
                            {entry.newValue || '(empty)'}
                          </pre>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Pagination */}
        {meta && meta.totalPages > 1 && (
          <div className="flex items-center justify-between pt-4 mt-4 border-t border-gray-100">
            <p className="text-xs text-gray-400">
              Page {meta.page} of {meta.totalPages} ({meta.totalItems} entries)
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                Previous
              </button>
              <button
                onClick={() => setPage((p) => Math.min(meta.totalPages, p + 1))}
                disabled={page >= meta.totalPages}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Next
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
