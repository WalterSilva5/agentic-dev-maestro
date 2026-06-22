import 'dotenv/config';

import { ClassSerializerInterceptor, Logger, RequestMethod } from '@nestjs/common';
import { NestFactory, Reflector } from '@nestjs/core';
import type { NestApplication } from '@nestjs/core';
import { SwaggerModule, DocumentBuilder } from '@nestjs/swagger';
import type { OpenAPIObject } from '@nestjs/swagger';
import { AppModule } from 'src/app.module';
import { AppConfigService } from 'src/modules/app-config/app-config.service';

async function bootstrap() {
  const app: NestApplication = await NestFactory.create(AppModule, {
    logger: ['debug', 'error', 'log', 'verbose', 'warn']
  });
  app.setGlobalPrefix('api', { exclude: [{ path: '/', method: RequestMethod.GET }] });

  app.useGlobalInterceptors(new ClassSerializerInterceptor(app.get(Reflector)));
  app.enableCors({
    origin: '*',
    methods: 'GET,HEAD,PUT,PATCH,POST,DELETE,OPTIONS',
    credentials: true,
    allowedHeaders: '*',
    preflightContinue: false
  });

  const config: Omit<OpenAPIObject, 'paths'> = new DocumentBuilder()
    .setVersion(process.env.PACKAGE_VERSION || '1.0')
    .setTitle('template API')
    .addBearerAuth()
    .build();
  const document: OpenAPIObject = SwaggerModule.createDocument(app, config);
  SwaggerModule.setup('api/docs', app, document);

  // Initialize default app configurations
  const appConfigService = app.get(AppConfigService);
  await appConfigService.initializeDefaults();

  const PORT: number = Number(process.env.PORT) || 5000;
  await app.listen(PORT);
  const logger: Logger = new Logger('NestApplication');
  logger.log(`Listenning on port ${PORT}`);
}
bootstrap();
