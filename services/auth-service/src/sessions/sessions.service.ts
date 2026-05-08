import {
  ForbiddenException,
  Injectable,
  Logger,
  NotFoundException,
} from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { AuditService } from '@adwp/kafka';

@Injectable()
export class SessionsService {
  private readonly logger = new Logger(SessionsService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly audit: AuditService,
  ) {}

  // ─── LIST ACTIVE SESSIONS ──────────────────────────────────────────────────

  async listSessions(userId: string, tenantId: string) {
    const sessions = await this.prisma.userSession.findMany({
      where: {
        userId,
        tenantId,
        expiresAt: { gt: new Date() },
      },
      select: {
        id: true,
        createdAt: true,
        expiresAt: true,
      },
      orderBy: { createdAt: 'desc' },
    });

    return sessions.map((session) => ({
      id: session.id,
      createdAt: session.createdAt,
      expiresAt: session.expiresAt,
    }));
  }

  // ─── REVOKE A SPECIFIC SESSION ─────────────────────────────────────────────

  async revokeSession(
    sessionId: string,
    userId: string,
    tenantId: string,
  ) {
    const session = await this.prisma.userSession.findUnique({
      where: { id: sessionId },
    });

    if (!session) {
      throw new NotFoundException(`Session "${sessionId}" not found`);
    }

    // Ensure the session belongs to the current user and tenant
    if (session.userId !== userId || session.tenantId !== tenantId) {
      throw new ForbiddenException(
        'You do not have permission to revoke this session',
      );
    }

    await this.prisma.userSession.delete({ where: { id: sessionId } });

    this.logger.log(
      `Session ${sessionId} revoked for user ${userId} in tenant ${tenantId}`,
    );

    await this.audit.publishAudit({
      tenantId,
      actorType: 'USER',
      actorId: userId,
      action: 'SESSION_REVOKED',
      entityType: 'USER_SESSION',
      entityId: sessionId,
    });

    return { message: 'Session revoked successfully' };
  }

  // ─── REVOKE ALL SESSIONS EXCEPT CURRENT ────────────────────────────────────

  async revokeAllSessions(
    userId: string,
    tenantId: string,
    currentToken: string,
  ) {
    // Find the current session to exclude it
    const currentSession = await this.prisma.userSession.findUnique({
      where: { token: currentToken },
    });

    const where: any = {
      userId,
      tenantId,
    };

    // Exclude the current session if found
    if (currentSession) {
      where.id = { not: currentSession.id };
    }

    const result = await this.prisma.userSession.deleteMany({ where });

    this.logger.log(
      `Revoked ${result.count} sessions for user ${userId} in tenant ${tenantId} (kept current)`,
    );

    await this.audit.publishAudit({
      tenantId,
      actorType: 'USER',
      actorId: userId,
      action: 'ALL_SESSIONS_REVOKED',
      entityType: 'USER_SESSION',
      entityId: userId,
      metadata: { revokedCount: result.count },
    });

    return {
      message: 'All other sessions revoked successfully',
      revokedCount: result.count,
    };
  }
}
