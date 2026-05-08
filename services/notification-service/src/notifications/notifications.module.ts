import { Module } from '@nestjs/common';
import { NotificationsController } from './notifications.controller';
import { NotificationsConsumer } from './notifications.consumer';
import { NotificationsService } from './notifications.service';
import { EmailChannel } from './channels/email.channel';
import { SmsChannel } from './channels/sms.channel';
import { PushChannel } from './channels/push.channel';
import { SlackChannel } from './channels/slack.channel';
import { WebhookChannel } from './channels/webhook.channel';

@Module({
  controllers: [NotificationsController, NotificationsConsumer],
  providers: [
    NotificationsService,
    EmailChannel,
    SmsChannel,
    PushChannel,
    SlackChannel,
    WebhookChannel,
  ],
  exports: [
    NotificationsService,
    EmailChannel,
    SmsChannel,
    PushChannel,
    SlackChannel,
    WebhookChannel,
  ],
})
export class NotificationsModule {}
