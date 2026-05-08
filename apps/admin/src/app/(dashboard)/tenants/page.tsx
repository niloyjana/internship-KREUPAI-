'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import {
  Building2,
  Search,
  Filter,
  Loader2,
  AlertCircle,
  Eye,
  Ban,
  RotateCcw,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { format } from 'date-fns';
import { getTenants, suspendTenant, reactivateTenant, type Tenant } from '@/lib/api/tenants.api';
import { cn } from '@/lib/utils';

const PAGE_SIZE = 20;

const planColors: Record<string, string> = {
  free: 'bg-gray-100 text-gray-700',
  starter: 'bg-blue-50 text-blue-700',
  pro: 'bg-purple-50 text-purple-700',
  enterprise: 'bg-amber-50 text-amber-700',
};

const statusColors: Record<string, string> = {
  active: 'bg-green-50 text-green-700',
  suspended: 'bg-red-50 text-red-700',
  trial: 'bg-amber-50 text-amber-700',
};

export default function TenantsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [planFilter, setPlanFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['admin-tenants', search, planFilter, statusFilter, page],
    queryFn: () =>
      getTenants({
        search: search || undefined,
        plan: planFilter || undefined,
        status: statusFilter || undefined,
        page,
        pageSize: PAGE_SIZE,
      }),
  });

  const suspendMutation = useMutation({
    mutationFn: suspendTenant,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-tenants'] }),
  });

  const reactivateMutation = useMutation({
    mutationFn: reactivateTenant,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-tenants'] }),
  });

  const tenants = data?.data ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Tenants</h1>
          <p className="text-sm text-gray-500 mt-1">Manage all platform tenants</p>
        </div>
        <div className="flex items-center gap-2">
          <Building2 className="w-5 h-5 text-gray-400" />
          <span className="text-sm text-gray-500">{total} total</span>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
        <div className="flex flex-col sm:flex-row gap-3">
          {/* Search */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              placeholder="Search tenants by name or slug..."
              className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
          </div>

          {/* Plan filter */}
          <select
            value={planFilter}
            onChange={(e) => { setPlanFilter(e.target.value); setPage(1); }}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="">All Plans</option>
            <option value="free">Free</option>
            <option value="starter">Starter</option>
            <option value="pro">Pro</option>
            <option value="enterprise">Enterprise</option>
          </select>

          {/* Status filter */}
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="">All Statuses</option>
            <option value="active">Active</option>
            <option value="suspended">Suspended</option>
            <option value="trial">Trial</option>
          </select>
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
          <p className="text-sm text-gray-500 mt-3">Loading tenants...</p>
        </div>
      )}

      {/* Error */}
      {isError && !isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <AlertCircle className="w-8 h-8 text-red-500 mb-3" />
          <p className="text-sm font-medium text-gray-700">Failed to load tenants</p>
        </div>
      )}

      {/* Table */}
      {!isLoading && !isError && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50">
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Name</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Slug</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Plan</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-600">Users</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-600">Agents</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Created</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-600">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {tenants.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center text-gray-500">
                      No tenants found.
                    </td>
                  </tr>
                ) : (
                  tenants.map((tenant) => (
                    <tr key={tenant.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 font-medium text-gray-900">{tenant.name}</td>
                      <td className="px-4 py-3 text-gray-500 font-mono text-xs">{tenant.slug}</td>
                      <td className="px-4 py-3">
                        <span className={cn('inline-block px-2 py-0.5 rounded-full text-xs font-medium capitalize', planColors[tenant.plan] || 'bg-gray-100 text-gray-700')}>
                          {tenant.plan}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={cn('inline-block px-2 py-0.5 rounded-full text-xs font-medium capitalize', statusColors[tenant.status] || 'bg-gray-100 text-gray-700')}>
                          {tenant.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right text-gray-600">{tenant.usersCount}</td>
                      <td className="px-4 py-3 text-right text-gray-600">{tenant.agentsCount}</td>
                      <td className="px-4 py-3 text-gray-500 text-xs">
                        {format(new Date(tenant.createdAt), 'MMM d, yyyy')}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Link
                            href={`/tenants/${tenant.id}`}
                            className="p-1.5 rounded-md text-gray-400 hover:text-primary-600 hover:bg-primary-50 transition-colors"
                            title="View details"
                          >
                            <Eye className="w-4 h-4" />
                          </Link>
                          {tenant.status === 'active' ? (
                            <button
                              onClick={() => suspendMutation.mutate(tenant.id)}
                              disabled={suspendMutation.isPending}
                              className="p-1.5 rounded-md text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                              title="Suspend tenant"
                            >
                              <Ban className="w-4 h-4" />
                            </button>
                          ) : tenant.status === 'suspended' ? (
                            <button
                              onClick={() => reactivateMutation.mutate(tenant.id)}
                              disabled={reactivateMutation.isPending}
                              className="p-1.5 rounded-md text-gray-400 hover:text-green-600 hover:bg-green-50 transition-colors"
                              title="Reactivate tenant"
                            >
                              <RotateCcw className="w-4 h-4" />
                            </button>
                          ) : null}
                        </div>
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
                <span className="text-xs text-gray-500 px-2">
                  {page} / {totalPages}
                </span>
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
