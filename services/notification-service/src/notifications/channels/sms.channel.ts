import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

/**
 * Twilio SMS notification channel.
 *
 * Uses the Twilio REST API to deliver SMS messages.
 * Falls back to dev-mode logging when credentials are not configured.
 */
@Injectable()
export class SmsChannel {
  private readonly logger = new Logger(SmsChannel.name);
  private readonly enabled: boolean;
  private readonly accountSid: string | undefined;
  private readonly authToken: string | undefined;
  private readonly fromNumber: string | undefined;

  constructor(private readonly config: ConfigService) {
    this.accountSid = this.config.get<string>('TWILIO_ACCOUNT_SID');
    this.authToken = this.config.get<string>('TWILIO_AUTH_TOKEN');
    this.fromNumber = this.config.get<string>('TWILIO_PHONE_NUMBER');

    if (this.accountSid && this.authToken && this.fromNumber) {
      this.enabled = true;
      this.logger.log('Twilio SMS channel initialized');
    } else {
      this.enabled = false;
      this.logger.warn('Twilio credentials not set — SMS channel disabled (dev mode)');
    }
  }

  async send(to: string, body: string): Promise<boolean> {
    if (!this.enabled) {
      this.logger.log(`[DEV] SMS to=${to} body="${body.slice(0, 80)}" (Twilio disabled)`);
      return true; // Return true in dev mode so the flow continues
    }

    try {
      const url = `https://api.twilio.com/2010-04-01/Accounts/${this.accountSid}/Messages.json`;

      const params = new URLSearchParams({
        To: to,
        From: this.fromNumber!,
        Body: body,
      });

      const res = await fetch(url, {
        method: 'POST',
        headers: {
          Authorization:
            'Basic ' +
            Buffer.from(`${this.accountSid}:${this.authToken}`).toString('base64'),
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: params.toString(),
      });

      if (!res.ok) {
        const errorBody = await res.text();
        this.logger.error(`Twilio API error ${res.status}: ${errorBody}`);
        return false;
      }

      const data = (await res.json()) as { sid: string };
      this.logger.log(`SMS sent to ${to} — sid=${data.sid}`);
      return true;
    } catch (error) {
      this.logger.error(
        `Failed to send SMS to ${to}: ${error instanceof Error ? error.message : error}`,
      );
      return false;
    }
  }
}
