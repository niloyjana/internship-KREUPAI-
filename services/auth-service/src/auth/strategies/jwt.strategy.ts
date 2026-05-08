import { Injectable, UnauthorizedException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { PassportStrategy } from '@nestjs/passport';
import { ExtractJwt, Strategy } from 'passport-jwt';
import { TokenRevocationService } from '../token-revocation.service';

export interface JwtPayload {
  sub: string; // userId
  tid: string; // tenantId (P5 spec shorthand)
  role: string;
  dept?: string; // department (optional)
  email: string;
  jti: string;
  iat: number;
  exp: number;
}

@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy, 'jwt') {
  constructor(
    configService: ConfigService,
    private readonly tokenRevocationService: TokenRevocationService,
  ) {
    const publicKey = configService.get<string>('JWT_PUBLIC_KEY');
    if (!publicKey) {
      throw new Error('JWT_PUBLIC_KEY environment variable is not set');
    }

    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      ignoreExpiration: false,
      algorithms: ['RS256'],
      secretOrKey: publicKey.replace(/\\n/g, '\n'),
    });
  }

  /**
   * Called by Passport after the JWT is decoded and verified.
   * The returned object is attached to `request.user`.
   *
   * Checks whether the token has been revoked (via Redis jti lookup)
   * before granting access.
   */
  async validate(payload: JwtPayload) {
    if (!payload.sub || !payload.tid) {
      throw new UnauthorizedException('AUTH_TOKEN_INVALID');
    }

    // Check if the token has been revoked
    if (payload.jti) {
      const revoked = await this.tokenRevocationService.isRevoked(payload.jti);
      if (revoked) {
        throw new UnauthorizedException('AUTH_TOKEN_REVOKED');
      }
    }

    return {
      userId: payload.sub,
      tenantId: payload.tid,
      role: payload.role,
      dept: payload.dept,
      email: payload.email,
    };
  }
}
