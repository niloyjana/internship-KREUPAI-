import { NestFactory } from '@nestjs/core';
import { ValidationPipe, VersioningType } from '@nestjs/common';
import { MicroserviceOptions, Transport } from '@nestjs/microservices';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  app.enableVersioning({ type: VersioningType.URI, defaultVersion: '1' });

  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      forbidNonWhitelisted: true,
      transform: true,
    }),
  );

  app.enableCors({
    origin: [process.env.PLATFORM_URL || 'http://localhost:3000', 'http://localhost:3001'],
    credentials: true,
  });

  // Kafka consumer — graceful degradation if broker unavailable
  try {
    app.connectMicroservice<MicroserviceOptions>({
      transport: Transport.KAFKA,
      options: {
        client: {
          clientId: 'auth-service',
          brokers: [process.env.KAFKA_BROKERS || 'localhost:9092'],
        },
        consumer: {
          groupId: 'auth-consumers',
        },
      },
    });
    await app.startAllMicroservices();
    console.log('[auth-service] Kafka consumer connected');
  } catch (error) {
    console.warn(
      `[auth-service] Kafka unavailable — running in HTTP-only mode: ${error instanceof Error ? error.message : error}`,
    );
  }

  const port = process.env.PORT || 3009;
  await app.listen(port);
  console.log(`[auth-service] Running on port ${port}`);
}

bootstrap();
