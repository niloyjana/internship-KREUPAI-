import React, { forwardRef } from 'react';
import { cn } from '../lib/utils';

export interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  label?: string;
  error?: string;
  helperText?: string;
  iconPrefix?: React.ReactNode;
  variant?: 'default' | 'error';
  inputSize?: 'sm' | 'md' | 'lg';
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label,
      error,
      helperText,
      iconPrefix,
      variant,
      inputSize = 'md',
      className,
      id,
      ...props
    },
    ref,
  ) => {
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);
    const hasError = variant === 'error' || !!error;

    const sizeStyles = {
      sm: 'px-3 py-1.5 text-xs',
      md: 'px-4 py-2.5 text-sm',
      lg: 'px-4 py-3 text-base',
    };

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-gray-700 mb-1.5"
          >
            {label}
          </label>
        )}

        <div className="relative">
          {iconPrefix && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
              {iconPrefix}
            </div>
          )}

          <input
            ref={ref}
            id={inputId}
            className={cn(
              'w-full rounded-lg border bg-white text-gray-900 placeholder:text-gray-400 outline-none transition-colors',
              sizeStyles[inputSize],
              iconPrefix && 'pl-10',
              hasError
                ? 'border-red-300 focus:border-red-500 focus:ring-2 focus:ring-red-500/20'
                : 'border-gray-300 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20',
              props.disabled && 'bg-gray-50 text-gray-500 cursor-not-allowed',
              className,
            )}
            {...props}
          />
        </div>

        {error && (
          <p className="mt-1.5 text-xs text-red-600">{error}</p>
        )}

        {helperText && !error && (
          <p className="mt-1.5 text-xs text-gray-400">{helperText}</p>
        )}
      </div>
    );
  },
);

Input.displayName = 'Input';
