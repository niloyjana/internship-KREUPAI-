import { createParamDecorator, ExecutionContext } from '@nestjs/common';

/**
 * Extracts the authenticated user object from the request.
 * Populated by the JWT strategy after token validation.
 *
 * Usage:
 *   @CurrentUser() user: JwtPayload
 *   @CurrentUser('userId') userId: string
 */
export const CurrentUser = createParamDecorator(
  (data: string | undefined, ctx: ExecutionContext) => {
    const request = ctx.switchToHttp().getRequest();
    const user = request.user;
    return data ? user?.[data] : user;
  },
);
