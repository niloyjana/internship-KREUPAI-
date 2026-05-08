'use client';

import React, { useState, useMemo } from 'react';
import { Search } from 'lucide-react';
import { cn } from '../lib/utils';
import { Table, type TableColumn } from './Table';
import { Pagination } from './Pagination';

export interface DataTableProps<T> {
  columns: TableColumn<T>[];
  data: T[];
  searchable?: boolean;
  searchPlaceholder?: string;
  searchKeys?: string[];
  pageSize?: number;
  pageSizeOptions?: number[];
  emptyMessage?: string;
  emptyIcon?: React.ReactNode;
  className?: string;
  headerActions?: React.ReactNode;
  getRowKey?: (row: T, index: number) => string | number;
  onRowClick?: (row: T, index: number) => void;
  striped?: boolean;
}

export function DataTable<T extends Record<string, unknown>>({
  columns,
  data,
  searchable = true,
  searchPlaceholder = 'Search...',
  searchKeys,
  pageSize: initialPageSize = 10,
  pageSizeOptions = [10, 25, 50],
  emptyMessage = 'No data available',
  emptyIcon,
  className,
  headerActions,
  getRowKey,
  onRowClick,
  striped = false,
}: DataTableProps<T>) {
  const [search, setSearch] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(initialPageSize);

  // Filter data by search
  const filteredData = useMemo(() => {
    if (!search.trim()) return data;

    const query = search.toLowerCase();
    const keys = searchKeys || columns.map((c) => c.key);

    return data.filter((row) =>
      keys.some((key) => {
        const val = row[key];
        if (val == null) return false;
        return String(val).toLowerCase().includes(query);
      }),
    );
  }, [data, search, searchKeys, columns]);

  // Paginate
  const totalPages = Math.ceil(filteredData.length / pageSize);
  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredData.slice(start, start + pageSize);
  }, [filteredData, currentPage, pageSize]);

  // Reset page when search changes
  const handleSearchChange = (value: string) => {
    setSearch(value);
    setCurrentPage(1);
  };

  const handlePageSizeChange = (size: number) => {
    setPageSize(size);
    setCurrentPage(1);
  };

  return (
    <div className={cn('space-y-4', className)}>
      {/* Toolbar */}
      {(searchable || headerActions) && (
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          {searchable && (
            <div className="relative w-full sm:w-auto">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => handleSearchChange(e.target.value)}
                placeholder={searchPlaceholder}
                className="w-full sm:w-72 rounded-lg border border-gray-300 bg-white pl-10 pr-4 py-2 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
              />
            </div>
          )}
          {headerActions && <div className="flex items-center gap-2">{headerActions}</div>}
        </div>
      )}

      {/* Table */}
      <Table
        columns={columns}
        data={paginatedData}
        emptyMessage={search ? `No results for "${search}"` : emptyMessage}
        emptyIcon={emptyIcon}
        getRowKey={getRowKey}
        onRowClick={onRowClick}
        striped={striped}
      />

      {/* Pagination */}
      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        totalItems={filteredData.length}
        pageSize={pageSize}
        pageSizeOptions={pageSizeOptions}
        onPageChange={setCurrentPage}
        onPageSizeChange={handlePageSizeChange}
        showPageSize
        itemLabel="results"
      />
    </div>
  );
}
