'use client';

import React, { useState, useMemo } from 'react';
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import { cn } from '../lib/utils';

export interface TableColumn<T> {
  key: string;
  header: string;
  render?: (row: T, index: number) => React.ReactNode;
  sortable?: boolean;
  align?: 'left' | 'center' | 'right';
  className?: string;
}

export interface TableProps<T> {
  columns: TableColumn<T>[];
  data: T[];
  emptyMessage?: string;
  emptyIcon?: React.ReactNode;
  className?: string;
  rowClassName?: string | ((row: T, index: number) => string);
  onRowClick?: (row: T, index: number) => void;
  getRowKey?: (row: T, index: number) => string | number;
  striped?: boolean;
}

type SortDirection = 'asc' | 'desc' | null;

export function Table<T extends Record<string, unknown>>({
  columns,
  data,
  emptyMessage = 'No data available',
  emptyIcon,
  className,
  rowClassName,
  onRowClick,
  getRowKey,
  striped = false,
}: TableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<SortDirection>(null);

  function handleSort(key: string) {
    if (sortKey === key) {
      if (sortDir === 'asc') {
        setSortDir('desc');
      } else if (sortDir === 'desc') {
        setSortKey(null);
        setSortDir(null);
      }
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  }

  const sortedData = useMemo(() => {
    if (!sortKey || !sortDir) return data;

    return [...data].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];

      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return sortDir === 'asc' ? -1 : 1;
      if (bVal == null) return sortDir === 'asc' ? 1 : -1;

      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortDir === 'asc'
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }

      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDir === 'asc' ? aVal - bVal : bVal - aVal;
      }

      return 0;
    });
  }, [data, sortKey, sortDir]);

  const alignStyles = {
    left: 'text-left',
    center: 'text-center',
    right: 'text-right',
  };

  if (data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        {emptyIcon && (
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gray-100 mb-3">
            {emptyIcon}
          </div>
        )}
        <p className="text-sm text-gray-400">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className={cn('overflow-x-auto', className)}>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100">
            {columns.map((col) => (
              <th
                key={col.key}
                className={cn(
                  'py-2.5 pr-4 font-medium text-gray-500',
                  alignStyles[col.align || 'left'],
                  col.sortable && 'cursor-pointer select-none hover:text-gray-700',
                  col.className,
                )}
                onClick={col.sortable ? () => handleSort(col.key) : undefined}
              >
                <div
                  className={cn(
                    'inline-flex items-center gap-1.5',
                    col.align === 'right' && 'flex-row-reverse',
                  )}
                >
                  {col.header}
                  {col.sortable && (
                    <span className="inline-flex">
                      {sortKey === col.key && sortDir === 'asc' ? (
                        <ArrowUp className="w-3.5 h-3.5" />
                      ) : sortKey === col.key && sortDir === 'desc' ? (
                        <ArrowDown className="w-3.5 h-3.5" />
                      ) : (
                        <ArrowUpDown className="w-3.5 h-3.5 text-gray-300" />
                      )}
                    </span>
                  )}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedData.map((row, rowIndex) => {
            const key = getRowKey ? getRowKey(row, rowIndex) : rowIndex;
            const rowCn =
              typeof rowClassName === 'function'
                ? rowClassName(row, rowIndex)
                : rowClassName;

            return (
              <tr
                key={key}
                onClick={onRowClick ? () => onRowClick(row, rowIndex) : undefined}
                className={cn(
                  'border-b border-gray-50 last:border-0 transition-colors',
                  onRowClick && 'cursor-pointer hover:bg-gray-50',
                  striped && rowIndex % 2 === 1 && 'bg-gray-50/50',
                  rowCn,
                )}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={cn(
                      'py-3 pr-4',
                      alignStyles[col.align || 'left'],
                      col.className,
                    )}
                  >
                    {col.render
                      ? col.render(row, rowIndex)
                      : (row[col.key] as React.ReactNode) ?? '--'}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
