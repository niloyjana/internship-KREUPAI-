import {
  CanActivate,
  ExecutionContext,
  Injectable,
  ForbiddenException,
  Logger,
} from '@nestjs/common';
import { EntitlementsService } from './entitlements.service';

/**
 * Guard that checks subscription status before allowing agent execution.
 *
 * Expects the request to contain:
 *   - request.user.tenantId (set by JwtAuthGuard)
 *   - request.params.agentId OR request.body.agentId
 *
 * Must be used AFTER JwtAuthGuard so that request.user is populated.
 */
@Injectable()
export class EntitlementGuard implements CanActivate {
  private readonly logger = new Logger(EntitlementGuard.name);

  constructor(private readonly entitlementsService: EntitlementsService) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest();
    const user = request.user;

    if (!user || !user.tenantId) {
      throw new ForbiddenException('TENANT_CONTEXT_REQUIRED');
    }

    const tenantId: string = user.tenantId;

    // Resolve agentId from route params or request body
    const agentId: string | undefined =
      request.params?.agentId || request.body?.agentId;

    if (!agentId) {
      throw new ForbiddenException('AGENT_ID_REQUIRED');
    }

    // Check entitlement
    const entitlement = await this.entitlementsService.checkEntitlement(
      tenantId,
      agentId,
    );

    if (!entitlement.isEntitled) {
      this.logger.warn(
        `Entitlement denied for tenant=${tenantId} agent=${agentId}: status=${entitlement.subscriptionStatus}`,
      );
      throw new ForbiddenException('NO_ACTIVE_SUBSCRIPTION');
    }

    if (!entitlement.isEnabled) {
      this.logger.warn(
        `Agent disabled for tenant=${tenantId} agent=${agentId}`,
      );
      throw new ForbiddenException('AGENT_DISABLED');
    }

    // Enforce usage quota
    await this.entitlementsService.enforceUsageQuota(tenantId, agentId);

    return true;
  }
}
