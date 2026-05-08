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
          clientId: 'integration-hub',
          brokers: [process.env.KAFKA_BROKERS || 'localhost:9092'],
        },
        consumer: {
          groupId: 'integration-consumers',
        },
      },
    });
    await app.startAllMicroservices();
    console.log('[integration-hub] Kafka consumer connected');
  } catch (error) {
    console.warn(
      `[integration-hub] Kafka unavailable — running in HTTP-only mode: ${error instanceof Error ? error.message : error}`,
    );
  }

  const port = process.env.PORT || 3006;
  await app.listen(port);
  console.log(`[integration-hub] Running on port ${port}`);
}

bootstrap();
