import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import * as sgMail from '@sendgrid/mail';

@Injectable()
export class EmailChannel {
  private readonly logger = new Logger(EmailChannel.name);
  private readonly enabled: boolean;

  constructor(private readonly config: ConfigService) {
    const apiKey = this.config.get<string>('SENDGRID_API_KEY');
    if (apiKey) {
      sgMail.setApiKey(apiKey);
      this.enabled = true;
      this.logger.log('SendGrid email channel initialized');
    } else {
      this.enabled = false;
      this.logger.warn('SENDGRID_API_KEY not set — email channel disabled (dev mode)');
    }
  }

  async send(params: { to: string; subject: string; body: string; from?: string }): Promise<boolean> {
    const from = params.from || this.config.get<string>('EMAIL_FROM') || 'noreply@adwp.io';

    if (!this.enabled) {
      this.logger.log(`[DEV] Email to=${params.to} subject="${params.subject}" (SendGrid disabled)`);
      return true; // Return true in dev mode so the flow continues
    }

    try {
      await sgMail.send({
        to: params.to,
        from,
        subject: params.subject,
        html: params.body,
      });
      this.logger.log(`Email sent to ${params.to}: "${params.subject}"`);
      return true;
    } catch (error) {
      this.logger.error(`Failed to send email to ${params.to}: ${error instanceof Error ? error.message : error}`);
      return false;
    }
  }
}
