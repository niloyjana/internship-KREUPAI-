'use client';

import { useRouter } from 'next/navigation';
import { Menu, LogOut, User, Search } from 'lucide-react';
import { useAuthStore } from '@/lib/stores/auth.store';
import { useCommandPalette } from '@/components/search';
import { NotificationBell } from '@/components/notifications/NotificationBell';

interface HeaderProps {
  onMenuClick: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const { openPalette } = useCommandPalette();

  async function handleLogout() {
    await logout();
    router.push('/login');
  }

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-gray-200/80 bg-white/80 backdrop-blur-sm px-4 lg:px-5">
      {/* Left side */}
      <div className="flex items-center gap-2">
        <button
          onClick={onMenuClick}
          className="lg:hidden p-1.5 rounded-lg text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition-colors"
          aria-label="Toggle sidebar"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Search trigger */}
        <button
          onClick={openPalette}
          className="flex items-center gap-2 h-8 pl-3 pr-2 rounded-lg border border-gray-200 bg-gray-50/80 text-gray-400 hover:text-gray-600 hover:bg-gray-100 hover:border-gray-300 transition-colors"
          aria-label="Search"
        >
          <Search className="w-3.5 h-3.5" />
          <span className="hidden md:inline text-[13px]">Search...</span>
          <kbd className="hidden md:inline-flex items-center gap-0.5 ml-1 px-1.5 py-0.5 text-[10px] font-medium text-gray-400 bg-white border border-gray-200 rounded">
            &#8984;K
          </kbd>
        </button>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-2">
        <NotificationBell />

        <div className="flex items-center gap-2">
          <div className="hidden sm:block text-right">
            <p className="text-[13px] font-medium text-gray-900 leading-tight">
              {user?.name || 'User'}
            </p>
            <p className="text-[11px] text-gray-500 leading-tight">{user?.role || 'Member'}</p>
          </div>

          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary-100 text-primary-700">
            {user?.avatarUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={user.avatarUrl}
                alt={user.name}
                className="w-8 h-8 rounded-full object-cover"
              />
            ) : (
              <User className="w-3.5 h-3.5" />
            )}
          </div>

          <button
            onClick={handleLogout}
            className="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
            title="Sign out"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </header>
  );
}
