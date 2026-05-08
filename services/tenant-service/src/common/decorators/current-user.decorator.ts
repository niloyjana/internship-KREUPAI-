import { createParamDecorator, ExecutionContext } from '@nestjs/common';

/**
 * Extracts the current authenticated user from the request object.
 * The user is attached by the JWT strategy after token validation.
 *
 * Usage:
 *   @CurrentUser() user: JwtPayload
 *   @CurrentUser('sub') userId: string
 */
export const CurrentUser = createParamDecorator(
  (data: string | undefined, ctx: ExecutionContext) => {
    const request = ctx.switchToHttp().getRequest();
    const user = request.user;
    return data ? user?.[data] : user;
  },
);
