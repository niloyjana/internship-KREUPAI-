'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  CheckSquare,
  Plug,
  BarChart3,
  CreditCard,
  Settings,
  Bot,
  X,
  ChevronDown,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

interface SubRoute {
  label: string;
  href: string;
}

interface NavItem {
  label: string;
  href: string;
  icon: typeof LayoutDashboard;
  activePrefix?: string;
  subRoutes?: SubRoute[];
}

const navItems: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  {
    label: 'Workforce',
    href: '/workforce/catalog',
    icon: Bot,
    activePrefix: '/workforce',
    subRoutes: [
      { label: 'Catalog', href: '/workforce/catalog' },
      { label: 'Active Agents', href: '/workforce/active' },
    ],
  },
  {
    label: 'Tasks',
    href: '/tasks/live',
    icon: CheckSquare,
    activePrefix: '/tasks',
    subRoutes: [
      { label: 'Live Queue', href: '/tasks/live' },
      { label: 'Task Queue', href: '/tasks/queue' },
      { label: 'Task History', href: '/tasks/history' },
      { label: 'Escalations', href: '/tasks/escalations' },
    ],
  },
  { label: 'Integrations', href: '/integrations', icon: Plug },
  {
    label: 'Analytics',
    href: '/analytics/performance',
    icon: BarChart3,
    activePrefix: '/analytics',
    subRoutes: [
      { label: 'Performance', href: '/analytics/performance' },
      { label: 'Cost', href: '/analytics/cost' },
      { label: 'Compliance', href: '/analytics/compliance' },
    ],
  },
  { label: 'Billing', href: '/billing', icon: CreditCard },
  { label: 'Settings', href: '/settings', icon: Settings, activePrefix: '/settings' },
];

export function Sidebar({ open, onClose }: SidebarProps) {
  const pathname = usePathname();
  const [expandedSections, setExpandedSections] = useState<Set<string>>(() => {
    const initial = new Set<string>();
    navItems.forEach((item) => {
      if (item.subRoutes) {
        const matchPrefix = item.activePrefix || item.href;
        if (
          pathname === item.href ||
          (matchPrefix !== '/dashboard' && pathname.startsWith(matchPrefix))
        ) {
          initial.add(item.label);
        }
      }
    });
    return initial;
  });

  function toggleSection(label: string) {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(label)) {
        next.delete(label);
      } else {
        next.add(label);
      }
      return next;
    });
  }

  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex w-60 flex-col bg-gray-950 transition-transform duration-200 ease-in-out lg:translate-x-0 lg:static lg:z-auto',
          open ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        {/* Logo */}
        <div className="flex h-14 items-center justify-between px-4">
          <Link href="/dashboard" className="flex items-center gap-2.5">
            <div className="flex items-center justify-center w-7 h-7 rounded-lg bg-primary-600 text-white">
              <Bot className="w-4 h-4" />
            </div>
            <span className="text-base font-bold text-white tracking-tight">AISA</span>
          </Link>
          <button
            onClick={onClose}
            className="lg:hidden p-1 rounded-md text-gray-500 hover:text-gray-300"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-2.5 py-3 space-y-0.5">
          {navItems.map((item) => {
            const matchPrefix = item.activePrefix || item.href;
            const isActive =
              pathname === item.href ||
              (matchPrefix !== '/dashboard' && pathname.startsWith(matchPrefix));
            const isExpanded = expandedSections.has(item.label);
            const hasSubRoutes = item.subRoutes && item.subRoutes.length > 0;

            return (
              <div key={item.href}>
                {/* Main nav item */}
                <div className="flex items-center">
                  <Link
                    href={item.href}
                    onClick={onClose}
                    className={cn(
                      'flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-[13px] font-medium transition-colors flex-1',
                      isActive
                        ? 'bg-white/10 text-white'
                        : 'text-gray-400 hover:bg-white/5 hover:text-gray-200',
                    )}
                  >
                    <item.icon
                      className={cn(
                        'w-[18px] h-[18px] flex-shrink-0',
                        isActive ? 'text-primary-400' : 'text-gray-500',
                      )}
                    />
                    {item.label}
                  </Link>
                  {hasSubRoutes && (
                    <button
                      onClick={() => toggleSection(item.label)}
                      className={cn(
                        'p-1 rounded-md transition-colors mr-0.5',
                        isActive
                          ? 'text-gray-400 hover:text-white'
                          : 'text-gray-600 hover:text-gray-400',
                      )}
                    >
                      <ChevronDown
                        className={cn(
                          'w-3.5 h-3.5 transition-transform duration-200',
                          isExpanded && 'rotate-180',
                        )}
                      />
                    </button>
                  )}
                </div>

                {/* Sub-routes */}
                {hasSubRoutes && isExpanded && (
                  <div className="ml-7 mt-0.5 space-y-0.5 border-l border-gray-800 pl-2.5">
                    {item.subRoutes!.map((sub) => {
                      const isSubActive = pathname === sub.href;
                      return (
                        <Link
                          key={sub.href}
                          href={sub.href}
                          onClick={onClose}
                          className={cn(
                            'flex items-center px-2.5 py-1.5 rounded-md text-[13px] transition-colors',
                            isSubActive
                              ? 'text-white font-medium'
                              : 'text-gray-500 hover:text-gray-300',
                          )}
                        >
                          {sub.label}
                        </Link>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-gray-800/50">
          <p className="text-[11px] text-gray-600">AI Digital Workforce Platform</p>
          <p className="text-[11px] text-gray-700 mt-0.5">v1.0.0</p>
        </div>
      </aside>
    </>
  );
}
