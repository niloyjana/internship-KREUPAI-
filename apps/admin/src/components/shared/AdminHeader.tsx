'use client';

import { useRouter } from 'next/navigation';
import { Menu, LogOut, User } from 'lucide-react';
import { useAuthStore } from '@/lib/stores/auth.store';

interface AdminHeaderProps {
  onMenuClick: () => void;
}

export function AdminHeader({ onMenuClick }: AdminHeaderProps) {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  async function handleLogout() {
    await logout();
    router.push('/login');
  }

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-gray-200 bg-white/80 backdrop-blur-sm px-4 lg:px-6">
      {/* Left side: hamburger + platform name */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          className="lg:hidden p-2 rounded-lg text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition-colors"
          aria-label="Toggle sidebar"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="hidden sm:block">
          <h2 className="text-sm font-medium text-gray-500">Platform Administration</h2>
        </div>
      </div>

      {/* Right side: user menu */}
      <div className="flex items-center gap-3">
        {/* User info */}
        <div className="flex items-center gap-3">
          <div className="hidden sm:block text-right">
            <p className="text-sm font-medium text-gray-900 leading-tight">
              {user?.name || 'Admin'}
            </p>
            <p className="text-xs text-gray-500 leading-tight">{user?.role || 'Platform Admin'}</p>
          </div>

          {/* Avatar */}
          <div className="flex items-center justify-center w-9 h-9 rounded-full bg-primary-100 text-primary-700">
            {user?.avatarUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={user.avatarUrl}
                alt={user.name}
                className="w-9 h-9 rounded-full object-cover"
              />
            ) : (
              <User className="w-4 h-4" />
            )}
          </div>

          {/* Logout button */}
          <button
            onClick={handleLogout}
            className="p-2 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
            title="Sign out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
}
