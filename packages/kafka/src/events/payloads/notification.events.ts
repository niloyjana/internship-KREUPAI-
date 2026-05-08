export interface NotificationRequestedPayload {
  recipientUserId: string | null;
  recipientTeam: string | null;
  channels: string[];
  eventType: string;
  priority: 'urgent' | 'normal' | 'low';
  subject: string;
  body: string;
  deepLinkUrl: string | null;
  metadata: Record<string, unknown> | null;
}

export interface NotificationDeliveredPayload {
  notificationId: string;
  channel: string;
  status: 'delivered' | 'failed' | 'bounced';
  providerRef: string | null;
}
