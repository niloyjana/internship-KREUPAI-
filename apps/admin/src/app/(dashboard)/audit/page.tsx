'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ScrollText,
  Search,
  Loader2,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Calendar,
} from 'lucide-react';
import { format } from 'date-fns';
import { getAuditLogs, type AuditLog } from '@/lib/api/audit.api';
import { cn } from '@/lib/utils';

const PAGE_SIZE = 25;

export default function AuditPage() {
  const [tenantFilter, setTenantFilter] = useState('');
  const [actorFilter, setActorFilter] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [page, setPage] = useState(1);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['admin-audit', tenantFilter, actorFilter, actionFilter, startDate, endDate, page],
    queryFn: () =>
      getAuditLogs({
        tenantId: tenantFilter || undefined,
        actor: actorFilter || undefined,
        action: actionFilter || undefined,
        startDate: startDate || undefined,
        endDate: endDate || undefined,
        page,
        pageSize: PAGE_SIZE,
      }),
  });

  const logs = data?.data ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  function resetFilters() {
    setTenantFilter('');
    setActorFilter('');
    setActionFilter('');
    setStartDate('');
    setEndDate('');
    setPage(1);
  }

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Audit Log</h1>
          <p className="text-sm text-gray-500 mt-1">Cross-tenant activity audit trail</p>
        </div>
        <div className="flex items-center gap-2">
          <ScrollText className="w-5 h-5 text-gray-400" />
          <span className="text-sm text-gray-500">{total} entries</span>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
          {/* Tenant filter */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={tenantFilter}
              onChange={(e) => { setTenantFilter(e.target.value); setPage(1); }}
              placeholder="Tenant ID..."
              className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
          </div>

          {/* Actor filter */}
          <input
            type="text"
            value={actorFilter}
            onChange={(e) => { setActorFilter(e.target.value); setPage(1); }}
            placeholder="Actor..."
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />

          {/* Action filter */}
          <input
            type="text"
            value={actionFilter}
            onChange={(e) => { setActionFilter(e.target.value); setPage(1); }}
            placeholder="Action..."
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />

          {/* Start date */}
          <input
            type="date"
            value={startDate}
            onChange={(e) => { setStartDate(e.target.value); setPage(1); }}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />

          {/* End date */}
          <input
            type="date"
            value={endDate}
            onChange={(e) => { setEndDate(e.target.value); setPage(1); }}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />

          {/* Reset */}
          <button
            onClick={resetFilters}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors"
          >
            Reset
          </button>
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
          <p className="text-sm text-gray-500 mt-3">Loading audit logs...</p>
        </div>
      )}

      {/* Error */}
      {isError && !isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <AlertCircle className="w-8 h-8 text-red-500 mb-3" />
          <p className="text-sm font-medium text-gray-700">Failed to load audit logs</p>
        </div>
      )}

      {/* Table */}
      {!isLoading && !isError && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50">
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Timestamp</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Tenant</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Actor</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Action</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Entity</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {logs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-12 text-center text-gray-500">
                      No audit log entries found.
                    </td>
                  </tr>
                ) : (
                  logs.map((log) => (
                    <tr key={log.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                        {format(new Date(log.timestamp), 'MMM d, yyyy HH:mm:ss')}
                      </td>
                      <td className="px-4 py-3 text-gray-700 font-medium">{log.tenantName}</td>
                      <td className="px-4 py-3 text-gray-600">{log.actor}</td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-0.5 rounded-full bg-gray-100 text-xs font-medium text-gray-700">
                          {log.action}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-600">
                        {log.entity}
                        {log.entityId && (
                          <span className="ml-1 text-xs text-gray-400 font-mono">
                            ({log.entityId.slice(0, 8)})
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500 max-w-xs truncate">
                        {log.details}
                      </td>
                    </tr>
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
