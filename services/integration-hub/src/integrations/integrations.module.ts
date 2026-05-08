import { Module } from '@nestjs/common';
import { KafkaModule } from '@adwp/kafka';
import { TokenVaultModule } from '../token-vault/token-vault.module';
import { IntegrationsController } from './integrations.controller';
import { IntegrationsConsumer } from './integrations.consumer';
import { OAuthController } from './oauth.controller';
import { WebhooksController } from './webhooks.controller';
import { IntegrationsService } from './integrations.service';
import { TokenRefreshService } from './token-refresh.service';
import { WebhooksService } from './webhooks.service';
import { ConnectorsModule } from './connectors/connectors.module';

@Module({
  imports: [
    TokenVaultModule,
    KafkaModule.register({
      clientId: 'integration-hub',
      brokers: [process.env.KAFKA_BROKERS || 'localhost:9092'],
      consumerGroupId: 'integration-consumers',
    }),
    ConnectorsModule,
  ],
  controllers: [IntegrationsController, IntegrationsConsumer, OAuthController, WebhooksController],
  providers: [IntegrationsService, TokenRefreshService, WebhooksService],
  exports: [IntegrationsService, ConnectorsModule],
})
export class IntegrationsModule {}
