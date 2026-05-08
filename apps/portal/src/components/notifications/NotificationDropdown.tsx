'use client';

import { useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Loader2, InboxIcon } from 'lucide-react';
import { getNotifications, markAsRead, markAllAsRead } from '@/lib/api/notifications.api';
import { NotificationItem } from './NotificationItem';
import type { Notification } from '@/lib/types/notification.types';

interface NotificationDropdownProps {
  onClose: () => void;
}

export function NotificationDropdown({ onClose }: NotificationDropdownProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        onClose();
      }
    }

    // Delay adding the listener to avoid the bell click immediately closing it
    const timeoutId = setTimeout(() => {
      document.addEventListener('mousedown', handleClickOutside);
    }, 0);

    return () => {
      clearTimeout(timeoutId);
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [onClose]);

  // Close on Escape key
  useEffect(() => {
    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        onClose();
      }
    }
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  // Fetch notifications
  const { data, isLoading } = useQuery({
    queryKey: ['notifications', { page: 1, pageSize: 10 }],
    queryFn: () => getNotifications({ page: 1, pageSize: 10 }),
  });

  const notifications = data?.notifications ?? [];

  // Mark single notification as read
  const markReadMutation = useMutation({
    mutationFn: markAsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unreadNotificationCount'] });
    },
  });

  // Mark all as read
  const markAllReadMutation = useMutation({
    mutationFn: markAllAsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unreadNotificationCount'] });
    },
  });

  function handleNotificationClick(notification: Notification) {
    if (!notification.read) {
      markReadMutation.mutate(notification.id);
    }
    if (notification.link) {
      router.push(notification.link);
      onClose();
    }
  }

  function handleMarkAllAsRead() {
    markAllReadMutation.mutate();
  }

  function handleViewAll() {
    router.push('/notifications');
    onClose();
  }

  const hasUnread = notifications.some((n) => !n.read);

  return (
    <div
      ref={dropdownRef}
      className="absolute right-0 top-full mt-2 w-[380px] bg-white rounded-lg border border-gray-200 shadow-lg z-50 overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-900">Notifications</h3>
        {hasUnread && (
          <button
            onClick={handleMarkAllAsRead}
            disabled={markAllReadMutation.isPending}
            className="text-xs font-medium text-primary-600 hover:text-primary-700 transition-colors disabled:opacity-50"
          >
            Mark all as read
          </button>
        )}
      </div>

      {/* Notification list */}
      <div className="max-h-[400px] overflow-y-auto">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
          </div>
        ) : notifications.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 px-4">
            <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gray-100 mb-3">
              <InboxIcon className="w-6 h-6 text-gray-400" />
            </div>
            <p className="text-sm font-medium text-gray-600">No notifications</p>
            <p className="text-xs text-gray-400 mt-1 text-center">
              You are all caught up. New notifications will appear here.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {notifications.map((notification) => (
              <NotificationItem
                key={notification.id}
                notification={notification}
                onClick={handleNotificationClick}
              />
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      {notifications.length > 0 && (
        <div className="border-t border-gray-100">
          <button
            onClick={handleViewAll}
            className="w-full px-4 py-2.5 text-xs font-medium text-primary-600 hover:bg-gray-50 transition-colors text-center"
          >
            View all notifications
          </button>
        </div>
      )}
    </div>
  );
}
