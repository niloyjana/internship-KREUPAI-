'use client';

import { AlertTriangle } from 'lucide-react';

interface UnsubscribeModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isPending: boolean;
  agentName: string;
}

export function UnsubscribeModal({
  open,
  onClose,
  onConfirm,
  isPending,
  agentName,
}: UnsubscribeModalProps) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="unsub-modal-title"
    >
      <div className="bg-white rounded-2xl shadow-xl border border-gray-200 max-w-md w-full mx-4 p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="flex items-center justify-center w-10 h-10 rounded-full bg-red-50">
            <AlertTriangle className="w-5 h-5 text-red-500" />
          </div>
          <div>
            <h3 id="unsub-modal-title" className="text-base font-semibold text-gray-900">
              Unsubscribe from agent?
            </h3>
            <p className="text-xs text-gray-500">This will stop all executions immediately.</p>
          </div>
        </div>
        <p className="text-sm text-gray-600 mb-5">
          You are about to unsubscribe from <strong>{agentName}</strong>. All running tasks will be
          cancelled, and you will lose access to activity history and settings.
        </p>
        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg border border-gray-200 text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isPending}
            className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-700 transition-colors disabled:opacity-60"
          >
            {isPending ? 'Unsubscribing...' : 'Yes, Unsubscribe'}
          </button>
        </div>
      </div>
    </div>
  );
}
