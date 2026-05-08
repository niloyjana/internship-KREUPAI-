import { Module } from '@nestjs/common';
import { JwtModule } from '@nestjs/jwt';
import { PassportModule } from '@nestjs/passport';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { AuthController } from './auth.controller';
import { AuthService } from './auth.service';
import { JwtStrategy } from './strategies/jwt.strategy';
import { TokenRevocationService } from './token-revocation.service';

@Module({
  imports: [
    PassportModule.register({ defaultStrategy: 'jwt' }),
    JwtModule.registerAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (configService: ConfigService) => {
        const privateKey = configService.get<string>('JWT_PRIVATE_KEY');
        const publicKey = configService.get<string>('JWT_PUBLIC_KEY');
        if (!privateKey) {
          throw new Error('JWT_PRIVATE_KEY environment variable is not set');
        }
        if (!publicKey) {
          throw new Error('JWT_PUBLIC_KEY environment variable is not set');
        }
        return {
          privateKey: privateKey.replace(/\\n/g, '\n'),
          publicKey: publicKey.replace(/\\n/g, '\n'),
          signOptions: {
            algorithm: 'RS256' as const,
            expiresIn: configService.get<string>('JWT_ACCESS_EXPIRY') || '15m',
            issuer: 'adwp-auth-service',
            audience: 'adwp-platform',
          },
          verifyOptions: {
            algorithms: ['RS256' as const],
            issuer: 'adwp-auth-service',
            audience: 'adwp-platform',
          },
        };
      },
    }),
  ],
  controllers: [AuthController],
  providers: [AuthService, JwtStrategy, TokenRevocationService],
  exports: [AuthService, JwtModule, TokenRevocationService],
})
export class AuthModule {}
