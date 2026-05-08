import {
  ArgumentsHost,
  Catch,
  ExceptionFilter,
  HttpException,
  HttpStatus,
  Logger,
} from '@nestjs/common';
import { randomUUID } from 'crypto';
import { Response } from 'express';

/**
 * Maps known HTTP statuses / messages to domain-specific error codes.
 */
function resolveErrorCode(status: number, message: string): string {
  // Notification-specific codes
  if (message.includes('PREFERENCE_NOT_FOUND')) return 'PREFERENCE_NOT_FOUND';

  // Auth codes
  if (message.includes('AUTH_INVALID_CREDENTIALS')) return 'AUTH_INVALID_CREDENTIALS';
  if (message.includes('AUTH_TOKEN_EXPIRED')) return 'AUTH_TOKEN_EXPIRED';
  if (message.includes('AUTH_TOKEN_INVALID')) return 'AUTH_TOKEN_INVALID';
  if (message.includes('AUTH_SESSION_EXPIRED')) return 'AUTH_SESSION_EXPIRED';
  if (message.includes('AUTH_USER_INACTIVE')) return 'AUTH_USER_INACTIVE';
  if (message.includes('AUTH_TENANT_INACTIVE')) return 'AUTH_TENANT_INACTIVE';
  if (message.includes('ACCESS_DENIED')) return 'ACCESS_DENIED';

  // Generic HTTP status mappings
  switch (status) {
    case HttpStatus.UNAUTHORIZED:
      return 'AUTH_UNAUTHORIZED';
    case HttpStatus.FORBIDDEN:
      return 'AUTH_FORBIDDEN';
    case HttpStatus.NOT_FOUND:
      return 'RESOURCE_NOT_FOUND';
    case HttpStatus.BAD_REQUEST:
      return 'VALIDATION_ERROR';
    case HttpStatus.CONFLICT:
      return 'RESOURCE_CONFLICT';
    case HttpStatus.TOO_MANY_REQUESTS:
      return 'RATE_LIMIT_EXCEEDED';
    default:
      return 'INTERNAL_ERROR';
  }
}

@Catch()
export class GlobalExceptionFilter implements ExceptionFilter {
  private readonly logger = new Logger(GlobalExceptionFilter.name);

  catch(exception: unknown, host: ArgumentsHost): void {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    const traceId = randomUUID();

    let status = HttpStatus.INTERNAL_SERVER_ERROR;
    let message = 'An unexpected error occurred';

    if (exception instanceof HttpException) {
      status = exception.getStatus();
      const exceptionResponse = exception.getResponse();

      if (typeof exceptionResponse === 'string') {
        message = exceptionResponse;
      } else if (typeof exceptionResponse === 'object' && exceptionResponse !== null) {
        const resp = exceptionResponse as Record<string, unknown>;
        // class-validator returns an array of messages
        if (Array.isArray(resp.message)) {
          message = resp.message.join('; ');
        } else if (typeof resp.message === 'string') {
          message = resp.message;
        }
      }
    } else if (exception instanceof Error) {
      message = exception.message;
      this.logger.error(
        `Unhandled exception [${traceId}]: ${exception.message}`,
        exception.stack,
      );
    }

    const code = resolveErrorCode(status, message);

    response.status(status).json({
      success: false,
      error: {
        code,
        message,
        traceId,
      },
    });
  }
}
