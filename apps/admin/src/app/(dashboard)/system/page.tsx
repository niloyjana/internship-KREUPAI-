'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import {
  Server,
  Database,
  Cpu,
  Wifi,
  Loader2,
  AlertCircle,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowRight,
} from 'lucide-react';
import { getHealthStatus } from '@/lib/api/system.api';
import { cn } from '@/lib/utils';

const statusConfig: Record<string, { icon: typeof CheckCircle2; color: string; bgColor: string }> = {
  healthy: { icon: CheckCircle2, color: 'text-green-600', bgColor: 'bg-green-50' },
  degraded: { icon: AlertTriangle, color: 'text-amber-600', bgColor: 'bg-amber-50' },
  down: { icon: XCircle, color: 'text-red-600', bgColor: 'bg-red-50' },
};

export default function SystemPage() {
  const { data: health, isLoading, isError } = useQuery({
    queryKey: ['admin-health'],
    queryFn: getHealthStatus,
    refetchInterval: 15000,
  });

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
        <p className="text-sm text-gray-500 mt-3">Checking system health...</p>
      </div>
    );
  }

  if (isError || !health) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <AlertCircle className="w-8 h-8 text-red-500 mb-3" />
        <p className="text-sm font-medium text-gray-700">Failed to load system health</p>
      </div>
    );
  }

  const overallConfig = statusConfig[health.overall] || statusConfig.down;
  const OverallIcon = overallConfig.icon;

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">System Health</h1>
          <p className="text-sm text-gray-500 mt-1">Real-time infrastructure monitoring</p>
        </div>
        <Link
          href="/system/dlq"
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          Dead Letter Queue
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      {/* Overall Status */}
      <div className={cn('rounded-lg border shadow-sm p-5 flex items-center gap-4', overallConfig.bgColor, health.overall === 'down' ? 'border-red-300' : health.overall === 'degraded' ? 'border-amber-300' : 'border-green-300')}>
        <OverallIcon className={cn('w-8 h-8', overallConfig.color)} />
        <div>
          <p className={cn('text-lg font-bold capitalize', overallConfig.color)}>
            System {health.overall}
          </p>
          <p className="text-sm text-gray-600">
            {health.services.filter((s) => s.status === 'healthy').length} of {health.services.length} services healthy
          </p>
        </div>
      </div>

      {/* Services Grid */}
      <div>
        <h2 className="text-base font-semibold text-gray-900 mb-4">Services</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {health.services.map((service) => {
            const svcConfig = statusConfig[service.status] || statusConfig.down;
            const SvcIcon = svcConfig.icon;
            return (
              <div key={service.name} className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Server className="w-4 h-4 text-gray-400" />
                    <p className="text-sm font-semibold text-gray-900">{service.name}</p>
                  </div>
                  <SvcIcon className={cn('w-5 h-5', svcConfig.color)} />
                </div>
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-500">Status</span>
                    <span className={cn('font-medium capitalize', svcConfig.color)}>
                      {service.status}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-500">Response Time</span>
                    <span className="text-gray-700">{service.responseTimeMs}ms</span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-500">Last Checked</span>
                    <span className="text-gray-700">
                      {new Date(service.lastChecked).toLocaleTimeString()}
                    </span>
                  </div>
                  {service.details && (
                    <p className="text-xs text-gray-400 mt-1">{service.details}</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Infrastructure: Kafka, Redis, Database */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Kafka */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <div className="flex items-center gap-2 mb-4">
            <Wifi className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">Kafka</h2>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Status</span>
              <span className={cn(
                'text-sm font-medium capitalize',
                health.kafka.status === 'connected' ? 'text-green-600' : 'text-red-600',
              )}>
                {health.kafka.status}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Brokers</span>
              <span className="text-sm font-medium text-gray-900">{health.kafka.brokers}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Topics</span>
              <span className="text-sm font-medium text-gray-900">{health.kafka.topics}</span>
            </div>
          </div>
        </div>

        {/* Redis */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <div className="flex items-center gap-2 mb-4">
            <Cpu className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">Redis</h2>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Status</span>
              <span className={cn(
                'text-sm font-medium capitalize',
                health.redis.status === 'connected' ? 'text-green-600' : 'text-red-600',
              )}>
                {health.redis.status}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Memory Usage</span>
              <span className="text-sm font-medium text-gray-900">{health.redis.memoryUsage}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Connected Clients</span>
              <span className="text-sm font-medium text-gray-900">{health.redis.connectedClients}</span>
            </div>
          </div>
        </div>

        {/* Database */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <div className="flex items-center gap-2 mb-4">
            <Database className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">Database</h2>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Status</span>
              <span className={cn(
                'text-sm font-medium capitalize',
                health.database.status === 'connected' ? 'text-green-600' : 'text-red-600',
              )}>
                {health.database.status}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Active Connections</span>
              <span className="text-sm font-medium text-gray-900">{health.database.activeConnections}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Pool Size</span>
              <span className="text-sm font-medium text-gray-900">{health.database.poolSize}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
