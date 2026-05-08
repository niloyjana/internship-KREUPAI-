'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import {
  ArrowLeft,
  AlertTriangle,
  Loader2,
  AlertCircle,
  RotateCcw,
  X,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { format } from 'date-fns';
import { getDlqEntries, retryDlqEntry, dismissDlqEntry, type DlqEntry } from '@/lib/api/system.api';
import { cn } from '@/lib/utils';

const PAGE_SIZE = 20;

const statusColors: Record<string, string> = {
  pending: 'bg-amber-50 text-amber-700',
  retried: 'bg-blue-50 text-blue-700',
  dismissed: 'bg-gray-100 text-gray-700',
};

export default function DlqPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['admin-dlq', statusFilter, page],
    queryFn: () =>
      getDlqEntries({
        status: statusFilter || undefined,
        page,
        pageSize: PAGE_SIZE,
      }),
  });

  const retryMutation = useMutation({
    mutationFn: retryDlqEntry,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-dlq'] }),
  });

  const dismissMutation = useMutation({
    mutationFn: dismissDlqEntry,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-dlq'] }),
  });

  const entries = data?.data ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <Link
          href="/system"
          className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to system health
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Dead Letter Queue</h1>
            <p className="text-sm text-gray-500 mt-1">Failed messages that need attention</p>
          </div>
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            <span className="text-sm text-gray-500">{total} entries</span>
          </div>
        </div>
      </div>

      {/* Filter */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        >
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="retried">Retried</option>
          <option value="dismissed">Dismissed</option>
        </select>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
          <p className="text-sm text-gray-500 mt-3">Loading DLQ entries...</p>
        </div>
      )}

      {/* Error */}
      {isError && !isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <AlertCircle className="w-8 h-8 text-red-500 mb-3" />
          <p className="text-sm font-medium text-gray-700">Failed to load DLQ entries</p>
        </div>
      )}

      {/* Table */}
      {!isLoading && !isError && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50">
                  <th className="w-8 px-4 py-3"></th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Topic</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Key</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Error</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-600">Retries</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Failed At</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-600">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {entries.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center text-gray-500">
                      No DLQ entries found.
                    </td>
                  </tr>
                ) : (
                  entries.map((entry) => (
                    <>
                      <tr key={entry.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-4 py-3">
                          <button
                            onClick={() => setExpandedRow(expandedRow === entry.id ? null : entry.id)}
                            className="p-0.5 rounded text-gray-400 hover:text-gray-600"
                          >
                            {expandedRow === entry.id ? (
                              <ChevronUp className="w-4 h-4" />
                            ) : (
                              <ChevronDown className="w-4 h-4" />
                            )}
                          </button>
                        </td>
                        <td className="px-4 py-3 font-mono text-xs text-gray-700">{entry.topic}</td>
                        <td className="px-4 py-3 font-mono text-xs text-gray-600">{entry.key}</td>
                        <td className="px-4 py-3 text-xs text-red-600 max-w-xs truncate">{entry.error}</td>
                        <td className="px-4 py-3">
                          <span className={cn('inline-block px-2 py-0.5 rounded-full text-xs font-medium capitalize', statusColors[entry.status] || 'bg-gray-100 text-gray-700')}>
                            {entry.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right text-gray-600">{entry.retryCount}</td>
                        <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                          {format(new Date(entry.failedAt), 'MMM d, HH:mm:ss')}
                        </td>
                        <td className="px-4 py-3 text-right">
                          {entry.status === 'pending' && (
                            <div className="flex items-center justify-end gap-1">
                              <button
                                onClick={() => retryMutation.mutate(entry.id)}
                                disabled={retryMutation.isPending}
                                className="p-1.5 rounded-md text-gray-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                                title="Retry"
                              >
                                <RotateCcw className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => dismissMutation.mutate(entry.id)}
                                disabled={dismissMutation.isPending}
                                className="p-1.5 rounded-md text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                                title="Dismiss"
                              >
                                <X className="w-4 h-4" />
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                      {expandedRow === entry.id && (
                        <tr key={`${entry.id}-detail`}>
                          <td colSpan={8} className="px-8 py-4 bg-gray-50">
                            <p className="text-xs font-medium text-gray-600 mb-2">Payload:</p>
                            <pre className="bg-white rounded-lg p-3 text-xs text-gray-700 overflow-x-auto border border-gray-200">
                              {JSON.stringify(entry.payload, null, 2)}
                            </pre>
                            <p className="text-xs font-medium text-gray-600 mt-3 mb-1">Full Error:</p>
                            <p className="text-xs text-red-600">{entry.error}</p>
                          </td>
                        </tr>
                      )}
                    </>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200">
              <p className="text-xs text-gray-500">
                Showing {(page - 1) * PAGE_SIZE + 1} to {Math.min(page * PAGE_SIZE, total)} of {total}
              </p>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-1.5 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="text-xs text-gray-500 px-2">{page} / {totalPages}</span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="p-1.5 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
