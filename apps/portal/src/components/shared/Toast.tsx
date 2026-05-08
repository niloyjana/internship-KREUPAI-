'use client';

import { useState, useEffect, useCallback, createContext, useContext } from 'react';
import { CheckCircle, AlertCircle, X } from 'lucide-react';
import { cn } from '@/lib/utils';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type ToastVariant = 'success' | 'error';

interface ToastMessage {
  id: number;
  variant: ToastVariant;
  title: string;
  description?: string;
}

interface ToastContextValue {
  toast: (opts: { variant: ToastVariant; title: string; description?: string }) => void;
}

/* ------------------------------------------------------------------ */
/*  Context                                                            */
/* ------------------------------------------------------------------ */

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within <ToastProvider>');
  return ctx;
}

/* ------------------------------------------------------------------ */
/*  Provider + Rendered Toasts                                         */
/* ------------------------------------------------------------------ */

let nextId = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const toast = useCallback(
    (opts: { variant: ToastVariant; title: string; description?: string }) => {
      const id = ++nextId;
      setToasts((prev) => [...prev, { id, ...opts }]);
    },
    [],
  );

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}

      {/* Toast container */}
      <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none print:hidden">
        {toasts.map((t) => (
          <ToastItem key={t.id} item={t} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

/* ------------------------------------------------------------------ */
/*  Single Toast                                                       */
/* ------------------------------------------------------------------ */

function ToastItem({
  item,
  onDismiss,
}: {
  item: ToastMessage;
  onDismiss: (id: number) => void;
}) {
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(item.id), 4000);
    return () => clearTimeout(timer);
  }, [item.id, onDismiss]);

  const Icon = item.variant === 'success' ? CheckCircle : AlertCircle;

  return (
    <div
      className={cn(
        'pointer-events-auto flex items-start gap-3 w-80 rounded-lg border shadow-lg p-4 animate-slide-up',
        item.variant === 'success' && 'bg-white border-green-200',
        item.variant === 'error' && 'bg-white border-red-200',
      )}
    >
      <Icon
        className={cn(
          'w-5 h-5 flex-shrink-0 mt-0.5',
          item.variant === 'success' && 'text-green-500',
          item.variant === 'error' && 'text-red-500',
        )}
      />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900">{item.title}</p>
        {item.description && (
          <p className="text-xs text-gray-500 mt-0.5">{item.description}</p>
        )}
      </div>
      <button
        onClick={() => onDismiss(item.id)}
        className="flex-shrink-0 text-gray-400 hover:text-gray-600 transition-colors"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
