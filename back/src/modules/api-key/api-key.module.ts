import { Module } from '@nestjs/common';
import { PrismaModule } from 'src/database/prisma/prisma.module';
import { CompaniesModule } from 'src/modules/companies/companies.module';

import { ApiKeyController } from './api-key.controller';
import { ApiKeyService } from './api-key.service';

@Module({
  imports: [PrismaModule, CompaniesModule],
  controllers: [ApiKeyController],
  providers: [ApiKeyService],
  exports: [ApiKeyService]
})
export class ApiKeyModule {}
