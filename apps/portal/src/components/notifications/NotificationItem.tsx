'use client';

import { Info, AlertTriangle, AlertCircle, CheckCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Notification, NotificationType } from '@/lib/types/notification.types';

const typeConfig: Record<
  NotificationType,
  { icon: typeof Info; iconColor: string; bgColor: string }
> = {
  info: {
    icon: Info,
    iconColor: 'text-blue-500',
    bgColor: 'bg-blue-50',
  },
  warning: {
    icon: AlertTriangle,
    iconColor: 'text-amber-500',
    bgColor: 'bg-amber-50',
  },
  error: {
    icon: AlertCircle,
    iconColor: 'text-red-500',
    bgColor: 'bg-red-50',
  },
  success: {
    icon: CheckCircle,
    iconColor: 'text-green-500',
    bgColor: 'bg-green-50',
  },
};

function formatTimeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return 'Just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  const weeks = Math.floor(days / 7);
  return `${weeks}w ago`;
}

interface NotificationItemProps {
  notification: Notification;
  onClick?: (notification: Notification) => void;
}

export function NotificationItem({ notification, onClick }: NotificationItemProps) {
  const config = typeConfig[notification.type] || typeConfig.info;
  const Icon = config.icon;

  return (
    <button
      onClick={() => onClick?.(notification)}
      className={cn(
        'flex items-start gap-3 w-full text-left px-4 py-3 transition-colors hover:bg-gray-50',
        !notification.read && 'bg-primary-50/30',
      )}
    >
      {/* Type icon */}
      <div
        className={cn(
          'flex items-center justify-center w-8 h-8 rounded-full flex-shrink-0 mt-0.5',
          config.bgColor,
        )}
      >
        <Icon className={cn('w-4 h-4', config.iconColor)} />
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <p
          className={cn(
            'text-sm leading-tight truncate',
            notification.read ? 'font-normal text-gray-700' : 'font-semibold text-gray-900',
          )}
        >
          {notification.title}
        </p>
        <p className="text-xs text-gray-500 mt-0.5 line-clamp-2 leading-relaxed">
          {notification.message}
        </p>
        <p className="text-xs text-gray-400 mt-1">{formatTimeAgo(notification.createdAt)}</p>
      </div>

      {/* Unread dot */}
      {!notification.read && (
        <span className="flex-shrink-0 w-2 h-2 rounded-full bg-primary-500 mt-2" />
      )}
    </button>
  );
}
