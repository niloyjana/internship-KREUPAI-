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
    origin: process.env.PLATFORM_URL || 'http://localhost:3000',
    credentials: true,
  });

  try {
    app.connectMicroservice<MicroserviceOptions>({
      transport: Transport.KAFKA,
      options: {
        client: {
          clientId: 'tenant-service',
          brokers: [process.env.KAFKA_BROKERS || 'localhost:9092'],
        },
        consumer: {
          groupId: 'tenant-consumers',
        },
      },
    });
    await app.startAllMicroservices();
    console.log('[tenant-service] Kafka consumer connected');
  } catch (error) {
    console.warn(
      `[tenant-service] Kafka unavailable — running in HTTP-only mode: ${error instanceof Error ? error.message : error}`,
    );
  }

  const port = process.env.PORT || 3002;
  await app.listen(port);
  console.log(`[tenant-service] Running on port ${port}`);
}

bootstrap();
