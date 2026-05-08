import { SetMetadata } from '@nestjs/common';

export const ROLES_KEY = 'roles';

/**
 * Decorator that sets the required roles for a route handler.
 * Usage: @Roles('PLATFORM_ADMIN', 'TENANT_ADMIN')
 */
export const Roles = (...roles: string[]) => SetMetadata(ROLES_KEY, roles);
