'use client';

import { useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Bell } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getUnreadCount } from '@/lib/api/notifications.api';
import { NotificationDropdown } from './NotificationDropdown';

export function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false);

  // Poll unread count every 30 seconds; back off on failure to avoid
  // spamming the console when the notification-service is not running.
  const { data } = useQuery({
    queryKey: ['unreadNotificationCount'],
    queryFn: getUnreadCount,
    refetchInterval: 30_000,
    retry: 1,
    retryDelay: 5_000,
  });

  const unreadCount = data?.count ?? 0;

  const handleToggle = useCallback(() => {
    setIsOpen((prev) => !prev);
  }, []);

  const handleClose = useCallback(() => {
    setIsOpen(false);
  }, []);

  return (
    <div className="relative">
      <button
        onClick={handleToggle}
        className={cn(
          'relative p-2 rounded-lg transition-colors',
          isOpen
            ? 'text-primary-600 bg-primary-50'
            : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100',
        )}
        aria-label="Notifications"
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        <Bell className="w-5 h-5" />

        {/* Unread badge */}
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[10px] font-bold leading-none">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && <NotificationDropdown onClose={handleClose} />}
    </div>
  );
}
