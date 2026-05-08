import React from 'react';
import { Inbox } from 'lucide-react';
import { cn } from '../lib/utils';

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center py-16 text-center',
        className,
      )}
    >
      <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gray-100 mb-4">
        {icon || <Inbox className="w-6 h-6 text-gray-400" />}
      </div>

      <h3 className="text-sm font-semibold text-gray-700">{title}</h3>

      {description && (
        <p className="text-xs text-gray-400 mt-1.5 max-w-sm">{description}</p>
      )}

      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
