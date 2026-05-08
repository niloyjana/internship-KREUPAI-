'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Building2,
  Bot,
  CreditCard,
  Server,
  ScrollText,
  Settings,
  Shield,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface AdminSidebarProps {
  open: boolean;
  onClose: () => void;
}

interface NavItem {
  label: string;
  href: string;
  icon: typeof LayoutDashboard;
  activePrefix?: string;
}

const navItems: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { label: 'Tenants', href: '/tenants', icon: Building2, activePrefix: '/tenants' },
  { label: 'Agents', href: '/agents', icon: Bot, activePrefix: '/agents' },
  { label: 'Billing', href: '/billing', icon: CreditCard, activePrefix: '/billing' },
  { label: 'System', href: '/system', icon: Server, activePrefix: '/system' },
  { label: 'Audit', href: '/audit', icon: ScrollText, activePrefix: '/audit' },
  { label: 'Settings', href: '/settings', icon: Settings, activePrefix: '/settings' },
];

export function AdminSidebar({ open, onClose }: AdminSidebarProps) {
  const pathname = usePathname();

  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-white border-r border-gray-200 transition-transform duration-200 ease-in-out lg:translate-x-0 lg:static lg:z-auto',
          open ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        {/* Logo */}
        <div className="flex h-16 items-center justify-between px-5 border-b border-gray-100">
          <Link href="/dashboard" className="flex items-center gap-2.5">
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary-600 text-white">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <span className="text-lg font-bold text-gray-900 tracking-tight">AISA</span>
              <span className="ml-1.5 text-xs font-medium text-primary-600 bg-primary-50 px-1.5 py-0.5 rounded">
                Admin
              </span>
            </div>
          </Link>
          <button
            onClick={onClose}
            className="lg:hidden p-1 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          {navItems.map((item) => {
            const matchPrefix = item.activePrefix || item.href;
            const isActive =
              pathname === item.href ||
              (matchPrefix !== '/dashboard' && pathname.startsWith(matchPrefix));

            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onClose}
                className={cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900',
                )}
              >
                <item.icon
                  className={cn(
                    'w-5 h-5 flex-shrink-0',
                    isActive ? 'text-primary-600' : 'text-gray-400',
                  )}
                />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-gray-100">
          <p className="text-xs text-gray-400">Platform Administration</p>
          <p className="text-xs text-gray-300 mt-0.5">v1.0.0</p>
        </div>
      </aside>
    </>
  );
}
