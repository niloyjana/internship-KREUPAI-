import { apiClient } from './client';
import type {
  NotificationsResponse,
  UnreadCountResponse,
} from '../types/notification.types';

/**
 * Fetch paginated notifications for the current user.
 */
export async function getNotifications(params?: {
  page?: number;
  pageSize?: number;
}): Promise<NotificationsResponse> {
  const { data } = await apiClient.get<NotificationsResponse>('/v1/notifications', {
    params,
  });
  return data;
}

/**
 * Fetch the unread notification count for the current user.
 */
export async function getUnreadCount(): Promise<UnreadCountResponse> {
  const { data } = await apiClient.get<UnreadCountResponse>('/v1/notifications/unread-count');
  return data;
}

/**
 * Mark a single notification as read.
 */
export async function markAsRead(notificationId: string): Promise<void> {
  await apiClient.patch(`/v1/notifications/${notificationId}/read`);
}

/**
 * Mark all notifications as read for the current user.
 */
export async function markAllAsRead(): Promise<void> {
  await apiClient.patch('/v1/notifications/read-all');
}
