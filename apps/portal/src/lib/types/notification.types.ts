/**
 * Types for the notification center.
 */

export type NotificationType = 'info' | 'warning' | 'error' | 'success';

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  read: boolean;
  createdAt: string;
  /** Optional link to navigate to when clicking the notification */
  link?: string;
}

export interface NotificationsResponse {
  notifications: Notification[];
  meta: {
    page: number;
    pageSize: number;
    totalItems: number;
    totalPages: number;
  };
}

export interface UnreadCountResponse {
  count: number;
}
