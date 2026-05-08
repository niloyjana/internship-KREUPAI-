'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  Receipt,
  Download,
  Search,
  ChevronLeft,
  ChevronRight,
  FileText,
} from 'lucide-react';
import { cn } from '@/lib/utils';

/* ------------------------------------------------------------------ */
/*  Sub-navigation                                                      */
/* ------------------------------------------------------------------ */

const billingTabs = [
  { label: 'Overview', href: '/billing' },
  { label: 'Invoices', href: '/billing/invoices' },
  { label: 'Usage', href: '/billing/usage' },
  { label: 'Plans', href: '/billing/plans' },
];

/* ------------------------------------------------------------------ */
/*  Types & Mock Data                                                   */
/* ------------------------------------------------------------------ */

type InvoiceStatus = 'paid' | 'pending' | 'overdue';

interface Invoice {
  id: string;
  invoiceNumber: string;
  period: string;
  amount: number;
  status: InvoiceStatus;
  date: string;
  downloadUrl: string;
}

const invoiceStatusStyles: Record<InvoiceStatus, string> = {
  paid: 'bg-green-50 text-green-700',
  pending: 'bg-amber-50 text-amber-700',
  overdue: 'bg-red-50 text-red-700',
};

const MOCK_INVOICES: Invoice[] = [
  { id: '1', invoiceNumber: 'INV-2026-003', period: 'Mar 2026', amount: 2450.00, status: 'pending', date: '2026-03-01T00:00:00Z', downloadUrl: '#' },
  { id: '2', invoiceNumber: 'INV-2026-002', period: 'Feb 2026', amount: 2180.50, status: 'paid', date: '2026-02-01T00:00:00Z', downloadUrl: '#' },
  { id: '3', invoiceNumber: 'INV-2026-001', period: 'Jan 2026', amount: 1950.00, status: 'paid', date: '2026-01-01T00:00:00Z', downloadUrl: '#' },
  { id: '4', invoiceNumber: 'INV-2025-012', period: 'Dec 2025', amount: 2100.75, status: 'paid', date: '2025-12-01T00:00:00Z', downloadUrl: '#' },
  { id: '5', invoiceNumber: 'INV-2025-011', period: 'Nov 2025', amount: 1875.25, status: 'paid', date: '2025-11-01T00:00:00Z', downloadUrl: '#' },
  { id: '6', invoiceNumber: 'INV-2025-010', period: 'Oct 2025', amount: 1640.00, status: 'paid', date: '2025-10-01T00:00:00Z', downloadUrl: '#' },
  { id: '7', invoiceNumber: 'INV-2025-009', period: 'Sep 2025', amount: 1520.50, status: 'paid', date: '2025-09-01T00:00:00Z', downloadUrl: '#' },
  { id: '8', invoiceNumber: 'INV-2025-008', period: 'Aug 2025', amount: 980.00, status: 'overdue', date: '2025-08-01T00:00:00Z', downloadUrl: '#' },
];

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(amount);
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/* ------------------------------------------------------------------ */
/*  Page Component                                                     */
/* ------------------------------------------------------------------ */

export default function BillingInvoicesPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 5;

  const filtered = MOCK_INVOICES.filter(
    (inv) =>
      inv.invoiceNumber.toLowerCase().includes(searchQuery.toLowerCase()) ||
      inv.period.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  const totalPages = Math.ceil(filtered.length / pageSize);
  const paginated = filtered.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const totalPaid = MOCK_INVOICES.filter((i) => i.status === 'paid').reduce((s, i) => s + i.amount, 0);
  const totalPending = MOCK_INVOICES.filter((i) => i.status === 'pending').reduce((s, i) => s + i.amount, 0);
  const totalOverdue = MOCK_INVOICES.filter((i) => i.status === 'overdue').reduce((s, i) => s + i.amount, 0);

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Billing</h1>
        <p className="text-sm text-gray-500 mt-1">
          View and download your invoice history.
        </p>
      </div>

      {/* Sub-navigation */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-6">
          {billingTabs.map((tab) => (
            <Link
              key={tab.href}
              href={tab.href}
              className={cn(
                'pb-3 text-sm font-medium border-b-2 transition-colors',
                tab.href === '/billing/invoices'
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
              )}
            >
              {tab.label}
            </Link>
          ))}
        </nav>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 rounded-lg bg-green-50 border border-green-200">
          <p className="text-xs font-medium text-green-600 uppercase tracking-wide">Total Paid</p>
          <p className="text-xl font-bold text-green-800 mt-1">{formatCurrency(totalPaid)}</p>
        </div>
        <div className="p-4 rounded-lg bg-amber-50 border border-amber-200">
          <p className="text-xs font-medium text-amber-600 uppercase tracking-wide">Pending</p>
          <p className="text-xl font-bold text-amber-800 mt-1">{formatCurrency(totalPending)}</p>
        </div>
        <div className="p-4 rounded-lg bg-red-50 border border-red-200">
          <p className="text-xs font-medium text-red-600 uppercase tracking-wide">Overdue</p>
          <p className="text-xl font-bold text-red-800 mt-1">{formatCurrency(totalOverdue)}</p>
        </div>
      </div>

      {/* Invoice Table */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Receipt className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-semibold text-gray-900">Invoice History</h2>
            <span className="ml-1 px-2 py-0.5 rounded-full bg-gray-100 text-xs font-medium text-gray-600">
              {MOCK_INVOICES.length}
            </span>
          </div>
          <div className="relative w-full sm:w-auto">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              placeholder="Search invoices..."
              className="w-full sm:w-56 rounded-lg border border-gray-300 bg-white pl-10 pr-4 py-2 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
            />
          </div>
        </div>

        <div className="p-6">
          {paginated.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16">
              <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gray-100 mb-3">
                <FileText className="w-6 h-6 text-gray-400" />
              </div>
              <p className="text-sm font-medium text-gray-600">No invoices found</p>
              <p className="text-xs text-gray-400 mt-1">
                {searchQuery ? 'Try a different search term.' : 'Invoices will appear here once generated.'}
              </p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100">
                      <th className="text-left py-2.5 pr-4 font-medium text-gray-500">Invoice</th>
                      <th className="text-left py-2.5 pr-4 font-medium text-gray-500">Period</th>
                      <th className="text-right py-2.5 pr-4 font-medium text-gray-500">Amount</th>
                      <th className="text-left py-2.5 pr-4 font-medium text-gray-500">Status</th>
                      <th className="text-left py-2.5 pr-4 font-medium text-gray-500">Date</th>
                      <th className="text-right py-2.5 font-medium text-gray-500">Download</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginated.map((invoice) => (
                      <tr key={invoice.id} className="border-b border-gray-50 last:border-0">
                        <td className="py-3 pr-4 font-medium text-gray-900">{invoice.invoiceNumber}</td>
                        <td className="py-3 pr-4 text-gray-600">{invoice.period}</td>
                        <td className="py-3 pr-4 text-right font-medium text-gray-900">
                          {formatCurrency(invoice.amount)}
                        </td>
                        <td className="py-3 pr-4">
                          <span
                            className={cn(
                              'inline-block px-2 py-0.5 rounded-full text-xs font-medium capitalize',
                              invoiceStatusStyles[invoice.status],
                            )}
                          >
                            {invoice.status}
                          </span>
                        </td>
                        <td className="py-3 pr-4 text-gray-600 text-xs">{formatDate(invoice.date)}</td>
                        <td className="py-3 text-right">
                          <button
                            onClick={() => {
                              if (invoice.downloadUrl && invoice.downloadUrl !== '#') {
                                window.open(invoice.downloadUrl, '_blank');
                              }
                            }}
                            className="inline-flex items-center gap-1 text-xs text-primary-600 hover:text-primary-700 font-medium transition-colors"
                          >
                            <Download className="w-3.5 h-3.5" />
                            PDF
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between pt-4">
                  <p className="text-xs text-gray-400">
                    Page {currentPage} of {totalPages} ({filtered.length} invoices)
                  </p>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                      disabled={currentPage <= 1}
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      <ChevronLeft className="w-3.5 h-3.5" />
                      Previous
                    </button>
                    <button
                      onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                      disabled={currentPage >= totalPages}
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      Next
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
