import { SetMetadata } from '@nestjs/common';

export const ROLES_KEY = 'roles';

/**
 * Restricts access to users who hold one of the specified roles.
 * Usage: @Roles('TENANT_ADMIN', 'PLATFORM_ADMIN')
 */
export const Roles = (...roles: string[]) => SetMetadata(ROLES_KEY, roles);
