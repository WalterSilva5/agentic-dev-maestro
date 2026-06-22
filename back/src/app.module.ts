import type { MiddlewareConsumer, NestModule } from '@nestjs/common';
import { Module, ValidationPipe } from '@nestjs/common';
import { APP_GUARD, APP_FILTER, APP_PIPE } from '@nestjs/core';
import { BullModule } from '@nestjs/bull';
import { ScheduleModule } from '@nestjs/schedule';

import { PrismaModule } from './database/prisma/prisma.module';
import { AppException } from './exceptions/app.exception';
import { AllExceptionsFilter } from './exceptions/exception.filter';
import { HTTPLoggerMiddleware } from './middleware/logger.middleware';
import { AppConfigModule } from './modules/app-config/app-config.module';
import { AuthModule } from './modules/auth/auth.module';
import { AtGuard } from './modules/auth/guards/at.guard';
import { CreditAccountModule } from './modules/credit-account/credit-account.module';
import { CreditTransactionModule } from './modules/credit-transaction/credit-transaction.module';
import { HealthModule } from './modules/health/health.module';
import { UserModule } from './modules/user/user.module';
// Agentic Dev Maestro — domínio
import { ApiKeyModule } from './modules/api-key/api-key.module';
import { CompaniesModule } from './modules/companies/companies.module';
import { ProjectsModule } from './modules/projects/projects.module';
import { TasksModule } from './modules/tasks/tasks.module';

@Module({
  controllers: [],
  providers: [
    {
      provide: APP_GUARD,
      useClass: AtGuard
    },
    {
      provide: APP_FILTER,
      useClass: AllExceptionsFilter
    },
    {
      provide: APP_PIPE,
      useValue: new ValidationPipe({
        transform: true,
        whitelist: true,
        forbidNonWhitelisted: false,
        skipMissingProperties: true,
        skipNullProperties: true,
        exceptionFactory: (error: any) => {
          return new AppException(error);
        }
      })
    }
  ],
  imports: [
    ScheduleModule.forRoot(),
    BullModule.forRoot({
      redis: {
        host: process.env.REDIS_HOST || 'localhost',
        port: parseInt(process.env.REDIS_PORT) || 6379,
      },
    }),
    PrismaModule,
    AppConfigModule,
    AuthModule,
    UserModule,
    CreditAccountModule,
    CreditTransactionModule,
    HealthModule,
    // Agentic Dev Maestro
    CompaniesModule,
    ApiKeyModule,
    ProjectsModule,
    TasksModule,
  ]
})
export class AppModule implements NestModule {
  configure(consumer: MiddlewareConsumer) {
    consumer.apply(HTTPLoggerMiddleware).forRoutes('*');
  }
}
