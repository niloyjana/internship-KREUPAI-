'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  Plug,
  Loader2,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  Unplug,
  Activity,
  Shield,
  ChevronLeft,
  ChevronRight,
  Check,
  ArrowUpRight,
  ArrowDownLeft,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  getConnection,
  getConnectionLogs,
  testConnection,
  deleteConnection,
} from '@/lib/api/integrations.api';
import type {
  IntegrationStatus,
  ConnectionTestResult,
} from '@/lib/types/integration.types';

/* ------------------------------------------------------------------ */
/*  Color maps                                                         */
/* ------------------------------------------------------------------ */

const statusColors: Record<IntegrationStatus, string> = {
  CONNECTED: 'bg-green-100 text-green-800',
  PENDING_AUTH: 'bg-amber-100 text-amber-800',
  ERROR: 'bg-red-100 text-red-800',
  EXPIRED: 'bg-orange-100 text-orange-800',
  DISCONNECTED: 'bg-gray-100 text-gray-800',
};

const statusIcons: Record<IntegrationStatus, typeof CheckCircle2> = {
  CONNECTED: CheckCircle2,
  PENDING_AUTH: Clock,
  ERROR: XCircle,
  EXPIRED: AlertTriangle,
  DISCONNECTED: Unplug,
};

const logStatusColors: Record<string, string> = {
  success: 'bg-green-100 text-green-800',
  error: 'bg-red-100 text-red-800',
  pending: 'bg-amber-100 text-amber-800',
};

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

/* ------------------------------------------------------------------ */
/*  Page Component                                                     */
/* ------------------------------------------------------------------ */

export default function ConnectionDetailPage() {
  const router = useRouter();
  const params = useParams();
  const queryClient = useQueryClient();
  const connectionId = params.connectionId as string;

  // UI state
  const [logsPage, setLogsPage] = useState(1);
  const [disconnectConfirm, setDisconnectConfirm] = useState(false);
  const [testResult, setTestResult] = useState<ConnectionTestResult | null>(null);
  const [isTesting, setIsTesting] = useState(false);

  // Fetch connection
  const {
    data: connection,
    isLoading: connectionLoading,
    isError: connectionError,
  } = useQuery({
    queryKey: ['integrationConnection', connectionId],
    queryFn: () => getConnection(connectionId),
  });

  // Fetch logs
  const {
    data: logsData,
    isLoading: logsLoading,
    isError: logsError,
  } = useQuery({
    queryKey: ['integrationConnectionLogs', connectionId, logsPage],
    queryFn: () => getConnectionLogs(connectionId, { page: logsPage, pageSize: 15 }),
  });

  // Test mutation
  const testMutation = useMutation({
    mutationFn: () => testConnection(connectionId),
    onSuccess: (result) => {
      setTestResult(result);
      setIsTesting(false);
    },
    onError: () => {
      setIsTesting(false);
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: () => deleteConnection(connectionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['integrationConnections'] });
      queryClient.invalidateQueries({ queryKey: ['integrationCatalog'] });
      router.push('/integrations');
    },
  });

  function handleTest() {
    setIsTesting(true);
    setTestResult(null);
    testMutation.mutate();
  }

  function handleDisconnect() {
    deleteMutation.mutate();
  }

  // Loading state
  if (connectionLoading) {
    return (
      <div className="p-6 lg:p-8 max-w-7xl mx-auto">
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
          <p className="text-sm text-gray-500 mt-3">Loading connection details...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (connectionError || !connection) {
    return (
      <div className="p-6 lg:p-8 max-w-7xl mx-auto">
        <div className="flex flex-col items-center justify-center py-20">
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-red-50 mb-3">
            <AlertCircle className="w-6 h-6 text-red-500" />
          </div>
          <p className="text-sm font-medium text-gray-700">Failed to load connection</p>
          <p className="text-xs text-gray-400 mt-1">
            The connection may not exist or an error occurred.
          </p>
          <Link
            href="/integrations"
            className="mt-4 inline-flex items-center gap-1.5 text-sm text-primary-600 hover:text-primary-700 font-medium"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Integrations
          </Link>
        </div>
      </div>
    );
  }

  const StatusIcon = statusIcons[connection.status] || Plug;

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Back Link */}
      <Link
        href="/integrations"
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 font-medium transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Integrations
      </Link>

      {/* ============================================================ */}
      {/* Header                                                       */}
      {/* ============================================================ */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="flex items-center justify-center w-12 h-12 rounded-lg bg-primary-50 text-primary-600 flex-shrink-0">
                <Plug className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">{connection.name}</h1>
                <div className="flex items-center gap-3 mt-1">
                  <p className="text-sm text-gray-500">
                    {connection.provider.replace(/_/g, ' ')}
                  </p>
                  <span
                    className={cn(
                      'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
                      statusColors[connection.status] || 'bg-gray-100 text-gray-800',
                    )}
                  >
                    <StatusIcon className="w-3 h-3" />
                    {connection.status.replace(/_/g, ' ')}
                  </span>
                </div>
              </div>
            </div>
            <div className="text-sm text-gray-400">
              Connected {formatDate(connection.createdAt)}
            </div>
          </div>

          {/* Error Banner */}
          {connection.lastErrorMessage && connection.status === 'ERROR' && (
            <div className="mt-4 flex items-start gap-3 p-3 rounded-lg bg-red-50 border border-red-200">
              <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-red-800">Connection Error</p>
                <p className="text-xs text-red-600 mt-0.5">{connection.lastErrorMessage}</p>
                {connection.lastErrorAt && (
                  <p className="text-xs text-red-400 mt-1">
                    Occurred {formatDateTime(connection.lastErrorAt)}
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ============================================================ */}
      {/* Connection Health                                             */}
      {/* ============================================================ */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">Connection Health</h2>
          </div>
        </div>
        <div className="p-6">
          <div className="flex flex-col sm:flex-row sm:items-center gap-4">
            <button
              onClick={handleTest}
              disabled={isTesting}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
            >
              {isTesting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Testing...
                </>
              ) : (
                <>
                  <Activity className="w-4 h-4" />
                  Test Connection
                </>
              )}
            </button>

            {testResult && (
              <div
                className={cn(
                  'flex items-center gap-3 px-4 py-3 rounded-lg border',
                  testResult.status === 'healthy'
                    ? 'bg-green-50 border-green-200'
                    : 'bg-red-50 border-red-200',
                )}
              >
                {testResult.status === 'healthy' ? (
                  <CheckCircle2 className="w-5 h-5 text-green-600" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-600" />
                )}
                <div>
                  <p
                    className={cn(
                      'text-sm font-medium',
                      testResult.status === 'healthy' ? 'text-green-800' : 'text-red-800',
                    )}
                  >
                    {testResult.status === 'healthy' ? 'Healthy' : 'Unhealthy'}
                  </p>
                  <div className="flex items-center gap-3 text-xs mt-0.5">
                    <span
                      className={
                        testResult.status === 'healthy' ? 'text-green-600' : 'text-red-600'
                      }
                    >
                      Response: {testResult.responseTimeMs}ms
                    </span>
                    <span
                      className={
                        testResult.permissionsValid ? 'text-green-600' : 'text-red-600'
                      }
                    >
                      Permissions: {testResult.permissionsValid ? 'Valid' : 'Invalid'}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {testMutation.isError && (
              <div className="flex items-center gap-2 text-sm text-red-600">
                <AlertCircle className="w-4 h-4" />
                Failed to test connection.
              </div>
            )}
          </div>

          {connection.lastSyncAt && (
            <p className="text-xs text-gray-400 mt-4">
              Last sync: {formatDateTime(connection.lastSyncAt)}
            </p>
          )}
        </div>
      </div>

      {/* ============================================================ */}
      {/* Scopes Granted                                                */}
      {/* ============================================================ */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">Scopes Granted</h2>
          </div>
        </div>
        <div className="p-6">
          {connection.scopesGranted.length === 0 ? (
            <p className="text-sm text-gray-400">No scopes granted for this connection.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {connection.scopesGranted.map((scope) => (
                <div
                  key={scope}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-gray-50"
                >
                  <Check className="w-4 h-4 text-green-500 flex-shrink-0" />
                  <span className="text-sm text-gray-700">{scope}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ============================================================ */}
      {/* Activity Logs                                                 */}
      {/* ============================================================ */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">Activity Logs</h2>
          </div>
        </div>

        {logsLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-primary-600" />
          </div>
        )}

        {logsError && (
          <div className="flex flex-col items-center justify-center py-12">
            <AlertCircle className="w-6 h-6 text-red-500 mb-2" />
            <p className="text-sm text-gray-500">Failed to load activity logs.</p>
          </div>
        )}

        {logsData && (
          <div className="p-6 space-y-4">
            {logsData.logs.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8">
                <Activity className="w-8 h-8 text-gray-300 mb-2" />
                <p className="text-sm text-gray-400">No activity logs yet.</p>
              </div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-100">
                        <th className="text-left py-2.5 pr-4 font-medium text-gray-500">
                          Direction
                        </th>
                        <th className="text-left py-2.5 pr-4 font-medium text-gray-500">
                          Operation
                        </th>
                        <th className="text-left py-2.5 pr-4 font-medium text-gray-500">
                          Status
                        </th>
                        <th className="text-left py-2.5 pr-4 font-medium text-gray-500">
                          Method
                        </th>
                        <th className="text-right py-2.5 pr-4 font-medium text-gray-500">
                          Response
                        </th>
                        <th className="text-right py-2.5 pr-4 font-medium text-gray-500">
                          Duration
                        </th>
                        <th className="text-left py-2.5 font-medium text-gray-500">
                          Timestamp
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {logsData.logs.map((log) => (
                        <tr
                          key={log.id}
                          className="border-b border-gray-50 last:border-0"
                        >
                          <td className="py-3 pr-4">
                            <span className="inline-flex items-center gap-1 text-xs text-gray-600">
                              {log.direction === 'outbound' ? (
                                <ArrowUpRight className="w-3.5 h-3.5 text-blue-500" />
                              ) : (
                                <ArrowDownLeft className="w-3.5 h-3.5 text-green-500" />
                              )}
                              {log.direction}
                            </span>
                          </td>
                          <td className="py-3 pr-4 font-medium text-gray-900">
                            {log.operation}
                          </td>
                          <td className="py-3 pr-4">
                            <span
                              className={cn(
                                'inline-block px-2 py-0.5 rounded-full text-xs font-medium',
                                logStatusColors[log.status] || 'bg-gray-100 text-gray-600',
                              )}
                            >
                              {log.status}
                            </span>
                          </td>
                          <td className="py-3 pr-4 text-gray-500 font-mono text-xs">
                            {log.httpMethod || '-'}
                          </td>
                          <td className="py-3 pr-4 text-right text-gray-500 font-mono text-xs">
                            {log.responseStatus != null ? log.responseStatus : '-'}
                          </td>
                          <td className="py-3 pr-4 text-right text-gray-500 text-xs">
                            {log.durationMs != null ? `${log.durationMs}ms` : '-'}
                          </td>
                          <td className="py-3 text-gray-500 text-xs whitespace-nowrap">
                            {formatDateTime(log.createdAt)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Error details for failed logs */}
                {logsData.logs.some((l) => l.errorMessage) && (
                  <div className="space-y-2">
                    {logsData.logs
                      .filter((l) => l.errorMessage)
                      .map((log) => (
                        <div
                          key={`err-${log.id}`}
                          className="flex items-start gap-2 p-3 rounded-lg bg-red-50 border border-red-100"
                        >
                          <AlertCircle className="w-3.5 h-3.5 text-red-400 flex-shrink-0 mt-0.5" />
                          <div>
                            <p className="text-xs font-medium text-red-700">{log.operation}</p>
                            <p className="text-xs text-red-600 mt-0.5">{log.errorMessage}</p>
                          </div>
                        </div>
                      ))}
                  </div>
                )}

                {/* Pagination */}
                {logsData.meta.totalPages > 1 && (
                  <div className="flex items-center justify-between pt-2">
                    <p className="text-xs text-gray-400">
                      Page {logsData.meta.page} of {logsData.meta.totalPages} (
                      {logsData.meta.totalItems} entries)
                    </p>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setLogsPage((p) => Math.max(1, p - 1))}
                        disabled={logsPage <= 1}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        <ChevronLeft className="w-3.5 h-3.5" />
                        Previous
                      </button>
                      <button
                        onClick={() =>
                          setLogsPage((p) => Math.min(logsData.meta.totalPages, p + 1))
                        }
                        disabled={logsPage >= logsData.meta.totalPages}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        Next
                        <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {/* ============================================================ */}
      {/* Actions                                                       */}
      {/* ============================================================ */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-4">Danger Zone</h2>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 p-4 rounded-lg border border-red-200 bg-red-50">
            <div>
              <p className="text-sm font-medium text-red-800">Disconnect this integration</p>
              <p className="text-xs text-red-600 mt-0.5">
                This will permanently remove the connection and revoke all permissions.
              </p>
            </div>
            <button
              onClick={() => setDisconnectConfirm(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-700 transition-colors flex-shrink-0"
            >
              <Unplug className="w-4 h-4" />
              Disconnect
            </button>
          </div>
        </div>
      </div>

      {/* ============================================================ */}
      {/* Disconnect Confirmation Dialog                                */}
      {/* ============================================================ */}
      {disconnectConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl border border-gray-200 p-6 max-w-md mx-4">
            <h3 className="text-lg font-semibold text-gray-900">
              Disconnect {connection.name}?
            </h3>
            <p className="text-sm text-gray-500 mt-2">
              This will remove the connection to{' '}
              {connection.provider.replace(/_/g, ' ')} and revoke all granted permissions.
              Any agents using this integration may stop working.
            </p>

            {deleteMutation.isError && (
              <div className="flex items-center gap-2 p-3 mt-3 rounded-lg bg-red-50 border border-red-200">
                <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
                <p className="text-sm text-red-700">
                  Failed to disconnect. Please try again.
                </p>
              </div>
            )}

            <div className="flex items-center justify-end gap-3 mt-6">
              <button
                onClick={() => setDisconnectConfirm(false)}
                className="px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDisconnect}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-700 disabled:opacity-60 transition-colors"
              >
                {deleteMutation.isPending ? 'Disconnecting...' : 'Confirm Disconnect'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
