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
          clientId: 'agent-registry',
          brokers: [process.env.KAFKA_BROKERS || 'localhost:9092'],
        },
        consumer: {
          groupId: 'agent-registry-group',
        },
      },
    });
    await app.startAllMicroservices();
    console.log('[agent-registry] Kafka consumer connected');
  } catch (error) {
    console.warn(
      `[agent-registry] Kafka unavailable — running in HTTP-only mode: ${error instanceof Error ? error.message : error}`,
    );
  }

  const port = process.env.PORT || 3003;
  await app.listen(port);
  console.log(`[agent-registry] Running on port ${port}`);
}

bootstrap();
