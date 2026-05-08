import { Injectable, UnauthorizedException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { PassportStrategy } from '@nestjs/passport';
import { ExtractJwt, Strategy } from 'passport-jwt';

export interface JwtPayload {
  sub: string; // userId
  tid: string; // tenantId (P5 spec shorthand)
  role: string;
  dept?: string; // department (optional)
  email: string;
  iat: number;
  exp: number;
}

@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy, 'jwt') {
  constructor(configService: ConfigService) {
    const pubKey = configService.get<string>('JWT_PUBLIC_KEY');
    if (!pubKey) {
      throw new Error('JWT_PUBLIC_KEY environment variable is not set');
    }

    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      ignoreExpiration: false,
      algorithms: ['RS256'],
      secretOrKey: pubKey.replace(/\\n/g, '\n'),
    });
  }

  /**
   * Called by Passport after the JWT is decoded and verified.
   * The returned object is attached to `request.user`.
   */
  validate(payload: JwtPayload) {
    if (!payload.sub || !payload.tid) {
      throw new UnauthorizedException('AUTH_TOKEN_INVALID');
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
