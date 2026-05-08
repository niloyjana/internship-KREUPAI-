'use client';

import React from 'react';
import { cn } from '../lib/utils';

export interface TabItem {
  key: string;
  label: string;
  icon?: React.ReactNode;
  disabled?: boolean;
}

export interface TabsProps {
  items: TabItem[];
  activeKey: string;
  onChange: (key: string) => void;
  variant?: 'underline' | 'pills';
  className?: string;
}

export function Tabs({
  items,
  activeKey,
  onChange,
  variant = 'underline',
  className,
}: TabsProps) {
  if (variant === 'pills') {
    return (
      <div className={cn('flex gap-2', className)}>
        {items.map((item) => {
          const isActive = activeKey === item.key;
          return (
            <button
              key={item.key}
              onClick={() => !item.disabled && onChange(item.key)}
              disabled={item.disabled}
              className={cn(
                'inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100',
                item.disabled && 'opacity-50 cursor-not-allowed',
              )}
            >
              {item.icon}
              {item.label}
            </button>
          );
        })}
      </div>
    );
  }

  return (
    <div className={cn('border-b border-gray-200', className)}>
      <nav className="flex gap-8" aria-label="Tabs">
        {items.map((item) => {
          const isActive = activeKey === item.key;
          return (
            <button
              key={item.key}
              onClick={() => !item.disabled && onChange(item.key)}
              disabled={item.disabled}
              className={cn(
                'flex items-center gap-2 pb-3 text-sm font-medium border-b-2 transition-colors -mb-px',
                isActive
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
                item.disabled && 'opacity-50 cursor-not-allowed',
              )}
            >
              {item.icon}
              {item.label}
            </button>
          );
        })}
      </nav>
    </div>
  );
}
