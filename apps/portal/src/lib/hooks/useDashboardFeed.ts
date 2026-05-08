'use client';

import { useCallback, useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useWebSocket, ConnectionStatus } from './useWebSocket';
import { useAuthStore } from '../stores/auth.store';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface ExecutionUpdateEvent {
  type: 'started' | 'step_completed' | 'completed' | 'failed';
  executionId: string;
  agentId?: string;
  status?: string;
  timestamp: string;
  [key: string]: any;
}

export interface DashboardMetricsEvent {
  hint: string;
  timestamp: string;
  [key: string]: any;
}

export interface TaskCreatedEvent {
  taskId: string;
  agentId?: string;
  priority?: string;
  timestamp: string;
  [key: string]: any;
}

export interface TaskResolvedEvent {
  taskId: string;
  decision?: string;
  timestamp: string;
  [key: string]: any;
}

/* ------------------------------------------------------------------ */
/*  Hook                                                               */
/* ------------------------------------------------------------------ */

/**
 * Subscribes to the `dashboard` WebSocket room and automatically
 * invalidates relevant react-query caches when real-time events arrive.
 *
 * This means the existing `useQuery` calls on the dashboard page will
 * re-fetch fresh data from the API whenever an event is pushed, giving
 * the user near-instant updates without manual polling.
 *
 * Returns the WebSocket connection status.
 */
export function useDashboardFeed(): { status: ConnectionStatus } {
  const queryClient = useQueryClient();
  const tenantId = useAuthStore((s) => s.user?.tenantId) ?? '';

  const onExecutionUpdated = useCallback(
    (_event: ExecutionUpdateEvent) => {
      // Invalidate dashboard + executions queries so they refetch
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['executions'] });
    },
    [queryClient],
  );

  const onDashboardMetrics = useCallback(
    (_event: DashboardMetricsEvent) => {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
    [queryClient],
  );

  const onTaskCreated = useCallback(
    (_event: TaskCreatedEvent) => {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['humanTasks'] });
    },
    [queryClient],
  );

  const onTaskResolved = useCallback(
    (_event: TaskResolvedEvent) => {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['humanTasks'] });
    },
    [queryClient],
  );

  const handlers = useMemo(
    () => ({
      'execution:updated': onExecutionUpdated,
      'dashboard:metrics': onDashboardMetrics,
      'task:created': onTaskCreated,
      'task:resolved': onTaskResolved,
    }),
    [onExecutionUpdated, onDashboardMetrics, onTaskCreated, onTaskResolved],
  );

  const { status } = useWebSocket({
    room: 'dashboard',
    tenantId,
    handlers,
    enabled: !!tenantId,
  });

  return { status };
}
