import React from 'react';
import { cn } from '../lib/utils';

export interface CardProps {
  title?: string;
  description?: string;
  footer?: React.ReactNode;
  headerAction?: React.ReactNode;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  className?: string;
  children: React.ReactNode;
}

const paddingStyles: Record<NonNullable<CardProps['padding']>, string> = {
  none: 'p-0',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
};

export function Card({
  title,
  description,
  footer,
  headerAction,
  padding = 'md',
  className,
  children,
}: CardProps) {
  const hasHeader = title || description || headerAction;

  return (
    <div
      className={cn(
        'bg-white rounded-lg border border-gray-200 shadow-sm',
        className,
      )}
    >
      {hasHeader && (
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-start justify-between">
            <div>
              {title && (
                <h3 className="text-base font-semibold text-gray-900">{title}</h3>
              )}
              {description && (
                <p className="text-sm text-gray-500 mt-1">{description}</p>
              )}
            </div>
            {headerAction && <div>{headerAction}</div>}
          </div>
        </div>
      )}

      <div className={paddingStyles[padding]}>{children}</div>

      {footer && (
        <div className="px-6 py-4 border-t border-gray-100">{footer}</div>
      )}
    </div>
  );
}
