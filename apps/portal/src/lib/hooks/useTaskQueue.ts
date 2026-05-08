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
  status?: string;
  timestamp: string;
  [key: string]: any;
}

export interface TaskCreatedEvent {
  taskId: string;
  executionId: string;
  agentId?: string;
  priority?: string;
  timestamp: string;
  [key: string]: any;
}

export interface TaskResolvedEvent {
  taskId: string;
  executionId: string;
  decision?: string;
  timestamp: string;
  [key: string]: any;
}

/* ------------------------------------------------------------------ */
/*  Hook                                                               */
/* ------------------------------------------------------------------ */

/**
 * Subscribes to the `tasks` WebSocket room and automatically
 * invalidates the executions / humanTasks react-query caches
 * when real-time events arrive.
 *
 * This gives the Live Queue page near-instant updates for:
 *  - New or changed workflow executions
 *  - Newly created human tasks
 *  - Resolved human tasks
 *
 * Returns the WebSocket connection status.
 */
export function useTaskQueue(): { status: ConnectionStatus } {
  const queryClient = useQueryClient();
  const tenantId = useAuthStore((s) => s.user?.tenantId) ?? '';

  const onExecutionUpdated = useCallback(
    (_event: ExecutionUpdateEvent) => {
      queryClient.invalidateQueries({ queryKey: ['executions'] });
    },
    [queryClient],
  );

  const onTaskCreated = useCallback(
    (_event: TaskCreatedEvent) => {
      queryClient.invalidateQueries({ queryKey: ['humanTasks'] });
    },
    [queryClient],
  );

  const onTaskResolved = useCallback(
    (_event: TaskResolvedEvent) => {
      queryClient.invalidateQueries({ queryKey: ['humanTasks'] });
      // Also refresh executions since the resolved task may unblock a step
      queryClient.invalidateQueries({ queryKey: ['executions'] });
    },
    [queryClient],
  );

  const handlers = useMemo(
    () => ({
      'execution:updated': onExecutionUpdated,
      'task:created': onTaskCreated,
      'task:resolved': onTaskResolved,
    }),
    [onExecutionUpdated, onTaskCreated, onTaskResolved],
  );

  const { status } = useWebSocket({
    room: 'tasks',
    tenantId,
    handlers,
    enabled: !!tenantId,
  });

  return { status };
}
