import {
  CallHandler,
  ExecutionContext,
  ForbiddenException,
  Injectable,
  NestInterceptor,
  Logger,
} from '@nestjs/common';
import { Observable } from 'rxjs';

/**
 * Interceptor that validates tenant context on routes with :tenantId param.
 *
 * Rules:
 * - PLATFORM_ADMIN can access any tenant
 * - TENANT_ADMIN / DEPARTMENT_MANAGER / END_USER / AUDITOR can only
 *   access the tenant from their JWT claim
 * - If the route has no :tenantId param, this interceptor does nothing
 */
@Injectable()
export class TenantContextInterceptor implements NestInterceptor {
  private readonly logger = new Logger(TenantContextInterceptor.name);

  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    const request = context.switchToHttp().getRequest();
    const user = request.user;

    // Skip for unauthenticated/public routes
    if (!user) {
      return next.handle();
    }

    const paramTenantId = request.params?.tenantId;

    // If no tenantId in route params, nothing to check
    if (!paramTenantId) {
      return next.handle();
    }

    // PLATFORM_ADMIN can access any tenant
    if (user.role === 'PLATFORM_ADMIN') {
      request.tenantId = paramTenantId;
      return next.handle();
    }

    // For all other roles, the tenantId in the JWT must match the route param
    if (user.tenantId !== paramTenantId) {
      this.logger.warn(
        `User ${user.sub} attempted to access tenant ${paramTenantId} but belongs to ${user.tenantId}`,
      );
      throw new ForbiddenException(
        'You do not have access to this tenant',
      );
    }

    request.tenantId = paramTenantId;
    return next.handle();
  }
}
