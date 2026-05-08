import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

/**
 * Firebase Cloud Messaging (FCM) push notification channel.
 *
 * Uses the FCM HTTP v1 API to deliver push notifications.
 * Falls back to dev-mode logging when the service account is not configured.
 */
@Injectable()
export class PushChannel {
  private readonly logger = new Logger(PushChannel.name);
  private readonly enabled: boolean;
  private readonly serviceAccount: string | undefined;

  constructor(private readonly config: ConfigService) {
    this.serviceAccount = this.config.get<string>('FCM_SERVICE_ACCOUNT');

    if (this.serviceAccount) {
      this.enabled = true;
      this.logger.log('Firebase Cloud Messaging push channel initialized');
    } else {
      this.enabled = false;
      this.logger.warn('FCM_SERVICE_ACCOUNT not set — push channel disabled (dev mode)');
    }
  }

  async send(
    deviceToken: string,
    title: string,
    body: string,
    data?: Record<string, string>,
  ): Promise<boolean> {
    if (!this.enabled) {
      this.logger.log(
        `[DEV] Push to=${deviceToken} title="${title}" body="${body.slice(0, 80)}" (FCM disabled)`,
      );
      return true; // Return true in dev mode so the flow continues
    }

    try {
      // Parse the service account JSON to extract project ID
      const serviceAccountJson = JSON.parse(this.serviceAccount!);
      const projectId = serviceAccountJson.project_id;

      const url = `https://fcm.googleapis.com/v1/projects/${projectId}/messages:send`;

      const message: Record<string, unknown> = {
        message: {
          token: deviceToken,
          notification: {
            title,
            body,
          },
          ...(data && Object.keys(data).length > 0 ? { data } : {}),
        },
      };

      const res = await fetch(url, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${serviceAccountJson.access_token ?? ''}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(message),
      });

      if (!res.ok) {
        const errorBody = await res.text();
        this.logger.error(`FCM API error ${res.status}: ${errorBody}`);
        return false;
      }

      const result = (await res.json()) as { name: string };
      this.logger.log(`Push sent to ${deviceToken} — name=${result.name}`);
      return true;
    } catch (error) {
      this.logger.error(
        `Failed to send push to ${deviceToken}: ${error instanceof Error ? error.message : error}`,
      );
      return false;
    }
  }
}
