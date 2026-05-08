import { Controller, Logger } from '@nestjs/common';
import { EventPattern, Payload } from '@nestjs/microservices';
import {
  TOPICS,
  BaseEvent,
  TenantConfigUpdatedPayload,
  IntegrationTokenRefreshedPayload,
} from '@adwp/kafka';

@Controller()
export class IntegrationsConsumer {
  private readonly logger = new Logger(IntegrationsConsumer.name);

  @EventPattern(TOPICS.TENANT_CONFIG_UPDATED)
  async handleTenantConfigUpdated(
    @Payload() event: BaseEvent<TenantConfigUpdatedPayload>,
  ): Promise<void> {
    this.logger.log(
      `[${event.tenantId}] Tenant config updated: ` +
        `section=${event.payload.configSection}, ` +
        `keys=${event.payload.changedKeys.join(', ')}`,
    );
    // TODO: refresh integration connection configs if relevant keys changed
  }

  @EventPattern(TOPICS.INTEGRATION_TOKEN_REFRESHED)
  async handleTokenRefreshed(
    @Payload() event: BaseEvent<IntegrationTokenRefreshedPayload>,
  ): Promise<void> {
    this.logger.log(
      `[${event.tenantId}] Integration token refreshed: ` +
        `connectionId=${event.payload.connectionId}, ` +
        `provider=${event.payload.provider}, ` +
        `expiresAt=${event.payload.expiresAt}`,
    );
    // Internal confirmation logging
  }
}
