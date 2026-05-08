import { Module } from '@nestjs/common';
import { JwtModule } from '@nestjs/jwt';
import { PassportModule } from '@nestjs/passport';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { JwtStrategy } from './jwt.strategy';

@Module({
  imports: [
    PassportModule.register({ defaultStrategy: 'jwt' }),
    JwtModule.registerAsync({
      imports: [ConfigModule],
      useFactory: (configService: ConfigService) => {
        const publicKey = configService.get<string>('JWT_PUBLIC_KEY');
        if (!publicKey) {
          throw new Error('JWT_PUBLIC_KEY environment variable is not set');
        }
        return {
          publicKey: publicKey.replace(/\\n/g, '\n'),
          verifyOptions: {
            algorithms: ['RS256'],
          },
        };
      },
      inject: [ConfigService],
    }),
  ],
  providers: [JwtStrategy],
  exports: [JwtModule],
})
export class AuthModule {}
