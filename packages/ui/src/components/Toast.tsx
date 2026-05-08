'use client';

import React, { useState, useEffect, useCallback, createContext, useContext } from 'react';
import { createPortal } from 'react-dom';
import { X, CheckCircle2, AlertCircle, AlertTriangle, Info } from 'lucide-react';
import { cn } from '../lib/utils';

export type ToastVariant = 'success' | 'error' | 'warning' | 'info';

export interface ToastItem {
  id: string;
  variant: ToastVariant;
  title: string;
  description?: string;
  duration?: number;
}

const variantStyles: Record<ToastVariant, { bg: string; border: string; icon: React.ElementType }> = {
  success: { bg: 'bg-green-50', border: 'border-green-200', icon: CheckCircle2 },
  error: { bg: 'bg-red-50', border: 'border-red-200', icon: AlertCircle },
  warning: { bg: 'bg-amber-50', border: 'border-amber-200', icon: AlertTriangle },
  info: { bg: 'bg-blue-50', border: 'border-blue-200', icon: Info },
};

const iconColors: Record<ToastVariant, string> = {
  success: 'text-green-600',
  error: 'text-red-600',
  warning: 'text-amber-600',
  info: 'text-blue-600',
};

/* ------------------------------------------------------------------ */
/*  Single Toast Component                                              */
/* ------------------------------------------------------------------ */

interface ToastEntryProps {
  toast: ToastItem;
  onDismiss: (id: string) => void;
}

function ToastEntry({ toast, onDismiss }: ToastEntryProps) {
  const style = variantStyles[toast.variant];
  const IconComponent = style.icon;

  useEffect(() => {
    const duration = toast.duration ?? 5000;
    if (duration <= 0) return;

    const timer = setTimeout(() => {
      onDismiss(toast.id);
    }, duration);

    return () => clearTimeout(timer);
  }, [toast.id, toast.duration, onDismiss]);

  return (
    <div
      className={cn(
        'flex items-start gap-3 px-4 py-3 rounded-lg border shadow-lg animate-slide-up max-w-sm w-full',
        style.bg,
        style.border,
      )}
    >
      <IconComponent className={cn('w-5 h-5 flex-shrink-0 mt-0.5', iconColors[toast.variant])} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900">{toast.title}</p>
        {toast.description && (
          <p className="text-xs text-gray-500 mt-0.5">{toast.description}</p>
        )}
      </div>
      <button
        onClick={() => onDismiss(toast.id)}
        className="p-0.5 rounded text-gray-400 hover:text-gray-600 transition-colors flex-shrink-0"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Toast Context and Provider                                          */
/* ------------------------------------------------------------------ */

interface ToastContextValue {
  toast: (item: Omit<ToastItem, 'id'>) => void;
  dismiss: (id: string) => void;
  dismissAll: () => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

let toastCounter = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const dismissAll = useCallback(() => {
    setToasts([]);
  }, []);

  const addToast = useCallback((item: Omit<ToastItem, 'id'>) => {
    const id = `toast-${++toastCounter}-${Date.now()}`;
    setToasts((prev) => [...prev, { ...item, id }]);
  }, []);

  return (
    <ToastContext.Provider value={{ toast: addToast, dismiss, dismissAll }}>
      {children}
      {typeof document !== 'undefined' &&
        toasts.length > 0 &&
        createPortal(
          <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2">
            {toasts.map((t) => (
              <ToastEntry key={t.id} toast={t} onDismiss={dismiss} />
            ))}
          </div>,
          document.body,
        )}
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return ctx;
}
