import {
  CallHandler,
  ExecutionContext,
  Injectable,
  NestInterceptor,
} from '@nestjs/common';
import { Observable } from 'rxjs';
import { PrismaService } from '../../prisma/prisma.service';

/**
 * Sets the PostgreSQL session variable `app.tenant_id` from the
 * authenticated user's JWT claims before every database-touching request.
 * This enables Row-Level Security (RLS) policies on the database side.
 */
@Injectable()
export class TenantContextInterceptor implements NestInterceptor {
  constructor(private readonly prisma: PrismaService) {}

  async intercept(
    context: ExecutionContext,
    next: CallHandler,
  ): Promise<Observable<unknown>> {
    const request = context.switchToHttp().getRequest();
    const user = request.user;

    if (user?.tenantId) {
      await this.prisma.setTenantId(user.tenantId);
    }

    return next.handle();
  }
}
