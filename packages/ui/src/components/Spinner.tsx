import React from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '../lib/utils';

export interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  label?: string;
}

const sizeStyles: Record<NonNullable<SpinnerProps['size']>, string> = {
  sm: 'w-4 h-4',
  md: 'w-6 h-6',
  lg: 'w-8 h-8',
};

export function Spinner({ size = 'md', className, label }: SpinnerProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center', className)}>
      <Loader2
        className={cn('animate-spin text-primary-600', sizeStyles[size])}
      />
      {label && (
        <p className="text-sm text-gray-500 mt-3">{label}</p>
      )}
    </div>
  );
}
