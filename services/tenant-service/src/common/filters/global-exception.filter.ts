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
import { Prisma } from '@prisma/client';

/**
 * Maps known HTTP statuses / messages to domain-specific error codes.
 */
function resolveErrorCode(status: number, message: string): string {
  if (message.includes('TENANT_NOT_FOUND')) return 'TENANT_NOT_FOUND';
  if (message.includes('TENANT_SUSPENDED')) return 'TENANT_SUSPENDED';
  if (message.includes('DUPLICATE_RESOURCE')) return 'DUPLICATE_RESOURCE';

  switch (status) {
    case HttpStatus.UNAUTHORIZED:
      return 'AUTH_UNAUTHORIZED';
    case HttpStatus.FORBIDDEN:
      return 'AUTH_INSUFFICIENT_PERMISSION';
    case HttpStatus.NOT_FOUND:
      return 'RESOURCE_NOT_FOUND';
    case HttpStatus.BAD_REQUEST:
      return 'VALIDATION_FAILED';
    case HttpStatus.CONFLICT:
      return 'DUPLICATE_RESOURCE';
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
    let field: string | null = null;

    if (exception instanceof HttpException) {
      status = exception.getStatus();
      const exceptionResponse = exception.getResponse();

      if (typeof exceptionResponse === 'string') {
        message = exceptionResponse;
      } else if (typeof exceptionResponse === 'object' && exceptionResponse !== null) {
        const resp = exceptionResponse as Record<string, unknown>;
        if (Array.isArray(resp.message)) {
          message = resp.message.join('; ');
          field = 'body';
        } else if (typeof resp.message === 'string') {
          message = resp.message;
        }
      }
    } else if (exception instanceof Prisma.PrismaClientKnownRequestError) {
      switch (exception.code) {
        case 'P2002':
          status = HttpStatus.CONFLICT;
          message = `Unique constraint violation on: ${(exception.meta?.target as string[])?.join(', ') || 'unknown field'}`;
          break;
        case 'P2025':
          status = HttpStatus.NOT_FOUND;
          message = 'Record not found';
          break;
        case 'P2003':
          status = HttpStatus.BAD_REQUEST;
          message = 'Foreign key constraint violation';
          break;
        default:
          status = HttpStatus.INTERNAL_SERVER_ERROR;
          message = 'Database error';
      }
    } else if (exception instanceof Prisma.PrismaClientValidationError) {
      status = HttpStatus.BAD_REQUEST;
      message = 'Invalid data provided';
    } else if (exception instanceof Error) {
      message = exception.message;
      this.logger.error(`Unhandled exception [${traceId}]: ${exception.message}`, exception.stack);
    }

    if (status >= 500) {
      this.logger.error(
        `[${traceId}] ${status}: ${message}`,
        exception instanceof Error ? exception.stack : String(exception),
      );
    }

    const code = resolveErrorCode(status, message);

    response.status(status).json({
      success: false,
      error: {
        code,
        message,
        field,
        traceId,
      },
    });
  }
}
