'use client';

import { X, Play, Zap, Loader2, CheckCircle2, AlertTriangle, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { AgentExecuteResponse } from '@/lib/types/runtime.types';

interface RunTaskModalProps {
  open: boolean;
  onClose: () => void;
  agentName: string;
  taskInput: string;
  onTaskInputChange: (value: string) => void;
  onExecute: (payload: Record<string, unknown>) => void;
  isPending: boolean;
  isError: boolean;
  error: Error | null;
  result: AgentExecuteResponse | null;
  onRunAnother: () => void;
}

export function RunTaskModal({
  open,
  onClose,
  agentName,
  taskInput,
  onTaskInputChange,
  onExecute,
  isPending,
  isError,
  error,
  result,
  onRunAnother,
}: RunTaskModalProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-xl border border-gray-200 max-w-lg w-full mx-4 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-full bg-primary-50">
              <Zap className="w-5 h-5 text-primary-600" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-gray-900">Run Task</h3>
              <p className="text-xs text-gray-500">Execute a task on {agentName}</p>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        {!result ? (
          <>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Task Description
              </label>
              <textarea
                rows={4}
                value={taskInput}
                onChange={(e) => onTaskInputChange(e.target.value)}
                placeholder="e.g. Process refund for order #ORD-4521, customer reports wrong item received"
                className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-none"
              />
            </div>
            <div className="flex justify-end gap-3">
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-lg border border-gray-200 text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => onExecute({ task: taskInput, source: 'portal_ui' })}
                disabled={!taskInput.trim() || isPending}
                className="inline-flex items-center gap-1.5 px-5 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors disabled:opacity-60"
              >
                {isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> Executing...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" /> Execute
                  </>
                )}
              </button>
            </div>
          </>
        ) : (
          <>
            <div
              className={cn(
                'rounded-xl border p-4 mb-4',
                result.status === 'completed'
                  ? 'bg-green-50 border-green-200'
                  : result.status === 'escalated'
                    ? 'bg-amber-50 border-amber-200'
                    : 'bg-red-50 border-red-200',
              )}
            >
              <div className="flex items-center gap-2 mb-2">
                {result.status === 'completed' ? (
                  <CheckCircle2 className="w-5 h-5 text-green-600" />
                ) : result.status === 'escalated' ? (
                  <AlertTriangle className="w-5 h-5 text-amber-600" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-red-600" />
                )}
                <span
                  className={cn(
                    'text-sm font-semibold',
                    result.status === 'completed'
                      ? 'text-green-800'
                      : result.status === 'escalated'
                        ? 'text-amber-800'
                        : 'text-red-800',
                  )}
                >
                  {result.status === 'completed'
                    ? 'Task Completed'
                    : result.status === 'escalated'
                      ? 'Escalated to Human'
                      : 'Task Failed'}
                </span>
              </div>
              <div className="flex items-center gap-4 text-xs text-gray-600 mb-3">
                <span>Duration: {result.durationMs}ms</span>
                {result.tokenUsed != null && <span>Tokens: {result.tokenUsed}</span>}
                {result.costUsd != null && <span>Cost: ${result.costUsd.toFixed(4)}</span>}
              </div>
              <pre className="bg-white/80 rounded-lg p-3 text-xs text-gray-700 overflow-auto max-h-48 border border-gray-100 font-mono">
                {JSON.stringify(result.output, null, 2)}
              </pre>
            </div>
            <div className="flex justify-end gap-3">
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-lg border border-gray-200 text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors"
              >
                Close
              </button>
              <button
                onClick={onRunAnother}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors"
              >
                <Play className="w-4 h-4" /> Run Another
              </button>
            </div>
          </>
        )}

        {isError && !result && (
          <div className="mt-3 flex items-center gap-2 text-sm text-red-600">
            <AlertCircle className="w-4 h-4" />
            {error instanceof Error
              ? error.message
              : 'Failed to execute. Ensure the AI Runtime is running.'}
          </div>
        )}
      </div>
    </div>
  );
}
