'use client';

import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import {
  Search,
  Filter,
  Plug,
  Loader2,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  Unplug,
  Activity,
  Plus,
  Key,
  ExternalLink,
  Shield,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  getIntegrationCatalog,
  getConnections,
  createConnection,
  deleteConnection,
  testConnection,
} from '@/lib/api/integrations.api';
import type {
  CatalogProvider,
  IntegrationConnection,
  IntegrationStatus,
  IntegrationCategory,
  IntegrationAuthType,
  ConnectionTestResult,
} from '@/lib/types/integration.types';

/* ------------------------------------------------------------------ */
/*  Color maps                                                         */
/* ------------------------------------------------------------------ */

const categoryColors: Record<string, string> = {
  CRM: 'bg-blue-100 text-blue-800',
  Email: 'bg-purple-100 text-purple-800',
  Calendar: 'bg-green-100 text-green-800',
  Accounting: 'bg-amber-100 text-amber-800',
  HR: 'bg-pink-100 text-pink-800',
  Support: 'bg-orange-100 text-orange-800',
  Productivity: 'bg-cyan-100 text-cyan-800',
  ERP: 'bg-indigo-100 text-indigo-800',
};

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

const CATEGORIES: { value: string; label: string }[] = [
  { value: '', label: 'All Categories' },
  { value: 'CRM', label: 'CRM' },
  { value: 'Email', label: 'Email' },
  { value: 'Calendar', label: 'Calendar' },
  { value: 'Accounting', label: 'Accounting' },
  { value: 'HR', label: 'HR' },
  { value: 'Support', label: 'Support' },
  { value: 'Productivity', label: 'Productivity' },
  { value: 'ERP', label: 'ERP' },
];

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

function formatRelativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return formatDate(dateStr);
}

/* ------------------------------------------------------------------ */
/*  Page Component                                                     */
/* ------------------------------------------------------------------ */

export default function IntegrationsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  // UI state
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [connectProvider, setConnectProvider] = useState<CatalogProvider | null>(null);
  const [disconnectTarget, setDisconnectTarget] = useState<IntegrationConnection | null>(null);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{
    connectionId: string;
    result: ConnectionTestResult;
  } | null>(null);

  // Connect dialog form state
  const [connectName, setConnectName] = useState('');
  const [connectApiKey, setConnectApiKey] = useState('');
  const [connectScopes, setConnectScopes] = useState<Set<string>>(new Set());

  // Fetch catalog
  const {
    data: catalog = [],
    isLoading: catalogLoading,
    isError: catalogError,
  } = useQuery({
    queryKey: ['integrationCatalog'],
    queryFn: getIntegrationCatalog,
  });

  // Fetch connections
  const {
    data: connections = [],
    isLoading: connectionsLoading,
    isError: connectionsError,
  } = useQuery({
    queryKey: ['integrationConnections'],
    queryFn: getConnections,
  });

  // Set of connected providers to filter catalog
  const connectedProviders = useMemo(
    () => new Set(connections.map((c) => c.provider)),
    [connections],
  );

  // Available providers (not yet connected)
  const availableProviders = useMemo(() => {
    let filtered = catalog.filter((p) => !connectedProviders.has(p.provider));

    if (category) {
      filtered = filtered.filter((p) => p.category === category);
    }

    if (search.trim()) {
      const q = search.toLowerCase();
      filtered = filtered.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          p.description.toLowerCase().includes(q) ||
          p.category.toLowerCase().includes(q),
      );
    }

    return filtered;
  }, [catalog, connectedProviders, category, search]);

  // Create connection mutation
  const createMutation = useMutation({
    mutationFn: createConnection,
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['integrationConnections'] });
      queryClient.invalidateQueries({ queryKey: ['integrationCatalog'] });
      resetConnectDialog();

      // If OAuth, redirect to auth URL
      if (response.authUrl) {
        window.location.href = response.authUrl;
      }
    },
  });

  // Delete connection mutation
  const deleteMutation = useMutation({
    mutationFn: deleteConnection,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['integrationConnections'] });
      queryClient.invalidateQueries({ queryKey: ['integrationCatalog'] });
      setDisconnectTarget(null);
    },
  });

  // Test connection mutation
  const testMutation = useMutation({
    mutationFn: testConnection,
    onSuccess: (result, connectionId) => {
      setTestResult({ connectionId, result });
      setTestingId(null);
    },
    onError: () => {
      setTestingId(null);
    },
  });

  function resetConnectDialog() {
    setConnectProvider(null);
    setConnectName('');
    setConnectApiKey('');
    setConnectScopes(new Set());
  }

  function openConnectDialog(provider: CatalogProvider) {
    setConnectProvider(provider);
    setConnectName('');
    setConnectApiKey('');
    setConnectScopes(new Set(provider.availableScopes));
  }

  function handleConnect() {
    if (!connectProvider) return;

    createMutation.mutate({
      provider: connectProvider.provider,
      name: connectName || connectProvider.name,
      authType: connectProvider.authType,
      scopes: connectProvider.authType === 'oauth2' ? Array.from(connectScopes) : undefined,
      apiKey: connectProvider.authType === 'api_key' ? connectApiKey : undefined,
    });
  }

  function handleTest(connectionId: string) {
    setTestingId(connectionId);
    setTestResult(null);
    testMutation.mutate(connectionId);
  }

  function toggleScope(scope: string) {
    setConnectScopes((prev) => {
      const next = new Set(prev);
      if (next.has(scope)) {
        next.delete(scope);
      } else {
        next.add(scope);
      }
      return next;
    });
  }

  const isLoading = catalogLoading || connectionsLoading;
  const isError = catalogError || connectionsError;

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Integrations</h1>
        <p className="text-sm text-gray-500 mt-1">
          Manage your third-party connections and add new integrations.
        </p>
      </div>

      {/* Global Loading */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
          <p className="text-sm text-gray-500 mt-3">Loading integrations...</p>
        </div>
      )}

      {/* Global Error */}
      {isError && !isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-red-50 mb-3">
            <AlertCircle className="w-6 h-6 text-red-500" />
          </div>
          <p className="text-sm font-medium text-gray-700">Failed to load integrations</p>
          <p className="text-xs text-gray-400 mt-1">Please try again later.</p>
        </div>
      )}

      {!isLoading && !isError && (
        <>
          {/* ============================================================ */}
          {/* SECTION 1: Connected Integrations                            */}
          {/* ============================================================ */}
          <section>
            <div className="flex items-center gap-2 mb-4">
              <Plug className="w-5 h-5 text-primary-600" />
              <h2 className="text-base font-semibold text-gray-900">Connected Integrations</h2>
              <span className="ml-1 px-2 py-0.5 rounded-full bg-gray-100 text-xs font-medium text-gray-600">
                {connections.length}
              </span>
            </div>

            {connections.length === 0 ? (
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
                <div className="flex flex-col items-center justify-center py-16">
                  <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gray-100 mb-3">
                    <Plug className="w-6 h-6 text-gray-400" />
                  </div>
                  <p className="text-sm font-medium text-gray-600">No connected integrations</p>
                  <p className="text-xs text-gray-400 mt-1">
                    Browse the catalog below to connect your first integration.
                  </p>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {connections.map((conn) => {
                  const StatusIcon = statusIcons[conn.status] || Plug;
                  const isCurrentlyTesting = testingId === conn.id;
                  const currentTestResult =
                    testResult?.connectionId === conn.id ? testResult.result : null;

                  return (
                    <div
                      key={conn.id}
                      className="bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow cursor-pointer flex flex-col"
                      onClick={() => router.push(`/integrations/${conn.id}`)}
                    >
                      {/* Card Header */}
                      <div className="p-5 pb-3">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-center gap-3 min-w-0">
                            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary-50 text-primary-600 flex-shrink-0">
                              <Plug className="w-5 h-5" />
                            </div>
                            <div className="min-w-0">
                              <h3 className="text-sm font-semibold text-gray-900 truncate">
                                {conn.name}
                              </h3>
                              <p className="text-xs text-gray-400 mt-0.5 truncate">
                                {conn.provider.replace(/_/g, ' ')}
                              </p>
                            </div>
                          </div>

                          {/* Status Badge */}
                          <span
                            className={cn(
                              'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium flex-shrink-0',
                              statusColors[conn.status] || 'bg-gray-100 text-gray-800',
                            )}
                          >
                            <StatusIcon className="w-3 h-3" />
                            {conn.status.replace(/_/g, ' ')}
                          </span>
                        </div>
                      </div>

                      {/* Details */}
                      <div className="px-5 pb-3 flex-1 space-y-2">
                        <div className="flex items-center gap-2 text-xs text-gray-500">
                          <Shield className="w-3.5 h-3.5 text-gray-400" />
                          <span>
                            {conn.scopesGranted.length} scope
                            {conn.scopesGranted.length !== 1 ? 's' : ''} granted
                          </span>
                        </div>
                        {conn.lastSyncAt && (
                          <div className="flex items-center gap-2 text-xs text-gray-500">
                            <Activity className="w-3.5 h-3.5 text-gray-400" />
                            <span>Last sync: {formatRelativeTime(conn.lastSyncAt)}</span>
                          </div>
                        )}
                        {conn.lastErrorMessage && conn.status === 'ERROR' && (
                          <div className="flex items-start gap-2 text-xs text-red-600">
                            <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                            <span className="line-clamp-2">{conn.lastErrorMessage}</span>
                          </div>
                        )}
                        {currentTestResult && (
                          <div
                            className={cn(
                              'flex items-center gap-2 text-xs',
                              currentTestResult.status === 'healthy'
                                ? 'text-green-600'
                                : 'text-red-600',
                            )}
                          >
                            {currentTestResult.status === 'healthy' ? (
                              <CheckCircle2 className="w-3.5 h-3.5" />
                            ) : (
                              <XCircle className="w-3.5 h-3.5" />
                            )}
                            <span>
                              {currentTestResult.status === 'healthy' ? 'Healthy' : 'Unhealthy'} (
                              {currentTestResult.responseTimeMs}ms)
                            </span>
                          </div>
                        )}
                      </div>

                      {/* Footer Actions */}
                      <div className="px-5 py-4 border-t border-gray-100 flex items-center justify-between">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleTest(conn.id);
                          }}
                          disabled={isCurrentlyTesting}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                          {isCurrentlyTesting ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Activity className="w-3.5 h-3.5" />
                          )}
                          {isCurrentlyTesting ? 'Testing...' : 'Test'}
                        </button>

                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setDisconnectTarget(conn);
                          }}
                          className="inline-flex items-center gap-1 text-xs text-red-500 hover:text-red-600 font-medium transition-colors"
                        >
                          <Unplug className="w-3.5 h-3.5" />
                          Disconnect
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {/* ============================================================ */}
          {/* SECTION 2: Available Integrations                            */}
          {/* ============================================================ */}
          <section>
            <div className="flex items-center gap-2 mb-4">
              <Plus className="w-5 h-5 text-primary-600" />
              <h2 className="text-base font-semibold text-gray-900">Add Integration</h2>
            </div>

            {/* Filter Bar */}
            <div className="flex flex-col sm:flex-row gap-3 mb-5">
              {/* Search */}
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search integrations..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 bg-white pl-10 pr-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
                />
              </div>

              {/* Category Filter */}
              <div className="relative">
                <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="appearance-none rounded-lg border border-gray-300 bg-white pl-10 pr-10 py-2.5 text-sm text-gray-900 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 cursor-pointer"
                >
                  {CATEGORIES.map((cat) => (
                    <option key={cat.value} value={cat.value}>
                      {cat.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Empty catalog state */}
            {availableProviders.length === 0 && (
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
                <div className="flex flex-col items-center justify-center py-16">
                  <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gray-100 mb-3">
                    <Plug className="w-6 h-6 text-gray-400" />
                  </div>
                  <p className="text-sm font-medium text-gray-600">No integrations found</p>
                  <p className="text-xs text-gray-400 mt-1">
                    {search || category
                      ? 'Try adjusting your search or filters.'
                      : 'All available integrations are already connected.'}
                  </p>
                </div>
              </div>
            )}

            {/* Available Provider Cards */}
            {availableProviders.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {availableProviders.map((provider) => (
                  <div
                    key={provider.provider}
                    className="bg-white rounded-lg border border-gray-200 shadow-sm flex flex-col"
                  >
                    {/* Card Header */}
                    <div className="p-5 pb-3">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-gray-50 text-gray-600 flex-shrink-0">
                            <Plug className="w-5 h-5" />
                          </div>
                          <div className="min-w-0">
                            <h3 className="text-sm font-semibold text-gray-900 truncate">
                              {provider.name}
                            </h3>
                            <div className="flex items-center gap-2 mt-1">
                              <span
                                className={cn(
                                  'inline-block px-2 py-0.5 rounded-full text-xs font-medium',
                                  categoryColors[provider.category] || 'bg-gray-100 text-gray-800',
                                )}
                              >
                                {provider.category}
                              </span>
                              <span className="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                                {provider.authType === 'oauth2' ? 'OAuth 2.0' : 'API Key'}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Description */}
                    <div className="px-5 pb-3 flex-1">
                      <p className="text-sm text-gray-500 line-clamp-2">{provider.description}</p>
                    </div>

                    {/* Footer: Connect button */}
                    <div className="px-5 py-4 border-t border-gray-100 flex items-center justify-end">
                      <button
                        onClick={() => openConnectDialog(provider)}
                        className="px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500/50 transition-colors"
                      >
                        Connect
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </>
      )}

      {/* ============================================================ */}
      {/* Connect Dialog                                                */}
      {/* ============================================================ */}
      {connectProvider && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl border border-gray-200 p-6 max-w-lg mx-4 w-full max-h-[90vh] overflow-y-auto">
            <div className="flex items-center gap-3 mb-5">
              <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary-50 text-primary-600">
                <Plug className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">
                  Connect {connectProvider.name}
                </h3>
                <p className="text-xs text-gray-500">
                  {connectProvider.authType === 'oauth2'
                    ? 'You will be redirected to authorize access.'
                    : 'Enter your API key to connect.'}
                </p>
              </div>
            </div>

            <div className="space-y-4">
              {/* Connection Name */}
              <div>
                <label
                  htmlFor="connection-name"
                  className="block text-sm font-medium text-gray-700 mb-1.5"
                >
                  Connection Name
                </label>
                <input
                  id="connection-name"
                  type="text"
                  placeholder={`My ${connectProvider.name}`}
                  value={connectName}
                  onChange={(e) => setConnectName(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
                />
              </div>

              {/* OAuth2: Scopes */}
              {connectProvider.authType === 'oauth2' &&
                connectProvider.availableScopes.length > 0 && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Requested Scopes
                    </label>
                    <div className="space-y-2 max-h-48 overflow-y-auto rounded-lg border border-gray-200 p-3">
                      {connectProvider.availableScopes.map((scope) => (
                        <label
                          key={scope}
                          className="flex items-center gap-2.5 cursor-pointer group"
                        >
                          <input
                            type="checkbox"
                            checked={connectScopes.has(scope)}
                            onChange={() => toggleScope(scope)}
                            className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                          />
                          <span className="text-sm text-gray-700 group-hover:text-gray-900">
                            {scope}
                          </span>
                        </label>
                      ))}
                    </div>
                  </div>
                )}

              {/* API Key: key input */}
              {connectProvider.authType === 'api_key' && (
                <div>
                  <label
                    htmlFor="api-key"
                    className="block text-sm font-medium text-gray-700 mb-1.5"
                  >
                    API Key
                  </label>
                  <div className="relative">
                    <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                      id="api-key"
                      type="password"
                      placeholder="Enter your API key"
                      value={connectApiKey}
                      onChange={(e) => setConnectApiKey(e.target.value)}
                      className="w-full rounded-lg border border-gray-300 bg-white pl-10 pr-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
                    />
                  </div>
                  <p className="text-xs text-gray-400 mt-1.5">
                    Your API key is encrypted and stored securely.
                  </p>
                </div>
              )}

              {/* Mutation error */}
              {createMutation.isError && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200">
                  <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
                  <p className="text-sm text-red-700">
                    Failed to create connection. Please try again.
                  </p>
                </div>
              )}
            </div>

            {/* Dialog Actions */}
            <div className="flex items-center justify-end gap-3 mt-6">
              <button
                onClick={resetConnectDialog}
                className="px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConnect}
                disabled={
                  createMutation.isPending ||
                  (connectProvider.authType === 'api_key' && !connectApiKey.trim())
                }
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
              >
                {createMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Connecting...
                  </>
                ) : connectProvider.authType === 'oauth2' ? (
                  <>
                    <ExternalLink className="w-4 h-4" />
                    Authorize
                  </>
                ) : (
                  'Connect'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* Disconnect Confirmation Dialog                                */}
      {/* ============================================================ */}
      {disconnectTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl border border-gray-200 p-6 max-w-md mx-4">
            <h3 className="text-lg font-semibold text-gray-900">
              Disconnect {disconnectTarget.name}?
            </h3>
            <p className="text-sm text-gray-500 mt-2">
              This will remove the connection to{' '}
              {disconnectTarget.provider.replace(/_/g, ' ')} and revoke all granted
              permissions. Any agents using this integration may stop working.
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
                onClick={() => setDisconnectTarget(null)}
                className="px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteMutation.mutate(disconnectTarget.id)}
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
