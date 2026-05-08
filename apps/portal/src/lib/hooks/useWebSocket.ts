'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import { io, Socket } from 'socket.io-client';

/* ------------------------------------------------------------------ */
/*  Configuration                                                      */
/* ------------------------------------------------------------------ */

const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ||
  process.env.NEXT_PUBLIC_WORKFLOW_SERVICE_URL ||
  'http://localhost:3004';

const RECONNECT_DELAY_MS = 3000;
const MAX_RECONNECT_ATTEMPTS = 10;

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected';

export interface UseWebSocketOptions {
  /** The namespace/room to subscribe to (e.g. 'dashboard', 'tasks'). */
  room: string;
  /** Tenant ID used for room scoping. */
  tenantId: string;
  /** Map of event names to handler functions. */
  handlers: Record<string, (payload: any) => void>;
  /** Whether the hook should connect. Defaults to true. */
  enabled?: boolean;
}

/* ------------------------------------------------------------------ */
/*  Hook                                                               */
/* ------------------------------------------------------------------ */

/**
 * Low-level hook that manages a Socket.IO connection to the
 * workflow-service WebSocket gateway.
 *
 * - Connects to `WS_URL/ws`
 * - Emits `subscribe:<room>` with `{ tenantId }` upon connection
 * - Registers the provided event handlers
 * - Auto-reconnects on disconnect (up to MAX_RECONNECT_ATTEMPTS)
 * - Cleans up on unmount
 */
export function useWebSocket({
  room,
  tenantId,
  handlers,
  enabled = true,
}: UseWebSocketOptions) {
  const socketRef = useRef<Socket | null>(null);
  const handlersRef = useRef(handlers);
  const reconnectAttemptsRef = useRef(0);
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');

  // Keep handlers ref up-to-date without re-triggering the effect
  useEffect(() => {
    handlersRef.current = handlers;
  }, [handlers]);

  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.removeAllListeners();
      socketRef.current.disconnect();
      socketRef.current = null;
    }
    setStatus('disconnected');
  }, []);

  useEffect(() => {
    if (!enabled || !tenantId) {
      disconnect();
      return;
    }

    setStatus('connecting');

    const socket = io(`${WS_URL}/ws`, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: RECONNECT_DELAY_MS,
      reconnectionAttempts: MAX_RECONNECT_ATTEMPTS,
    });

    socketRef.current = socket;

    socket.on('connect', () => {
      reconnectAttemptsRef.current = 0;
      setStatus('connected');

      // Join the tenant-scoped room
      socket.emit(`subscribe:${room}`, { tenantId });
    });

    socket.on('disconnect', () => {
      setStatus('disconnected');
    });

    socket.on('reconnect_attempt', (attempt: number) => {
      reconnectAttemptsRef.current = attempt;
      setStatus('connecting');
    });

    socket.on('reconnect_failed', () => {
      setStatus('disconnected');
    });

    // Register all event handlers
    const eventNames = Object.keys(handlersRef.current);
    const wrappedHandlers: Record<string, (data: any) => void> = {};

    eventNames.forEach((event) => {
      const wrapped = (data: any) => {
        handlersRef.current[event]?.(data);
      };
      wrappedHandlers[event] = wrapped;
      socket.on(event, wrapped);
    });

    return () => {
      // Remove registered handlers
      eventNames.forEach((event) => {
        socket.off(event, wrappedHandlers[event]);
      });
      socket.removeAllListeners();
      socket.disconnect();
      socketRef.current = null;
      setStatus('disconnected');
    };
    // Re-connect when room or tenantId changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [room, tenantId, enabled]);

  return { status, disconnect };
}
