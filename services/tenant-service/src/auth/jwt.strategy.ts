import { Injectable, UnauthorizedException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { PassportStrategy } from '@nestjs/passport';
import { ExtractJwt, Strategy } from 'passport-jwt';

export interface JwtPayload {
  sub: string; // userId
  email: string;
  name: string;
  tid: string; // tenantId (P5 spec shorthand)
  role: string; // UserRole
  dept?: string; // department (optional)
  iat?: number;
  exp?: number;
}

@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
  constructor(configService: ConfigService) {
    const publicKey = configService.get<string>('JWT_PUBLIC_KEY');

    if (!publicKey) {
      throw new Error(
        'JWT_PUBLIC_KEY environment variable is not set. ' +
          'This service requires the public key from auth-service to validate tokens.',
      );
    }

    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      ignoreExpiration: false,
      algorithms: ['RS256'],
      secretOrKey: publicKey.replace(/\\n/g, '\n'),
    });
  }

  async validate(payload: JwtPayload) {
    if (!payload.sub || !payload.email) {
      throw new UnauthorizedException('Invalid token payload');
    }

    return {
      sub: payload.sub,
      email: payload.email,
      name: payload.name,
      tenantId: payload.tid,
      role: payload.role,
      dept: payload.dept,
    };
  }
}
