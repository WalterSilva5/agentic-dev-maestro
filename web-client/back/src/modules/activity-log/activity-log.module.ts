import { Global, Module } from '@nestjs/common';
import { PrismaModule } from 'src/database/prisma/prisma.module';
import { AccessModule } from 'src/modules/access/access.module';

import { ActivityLogController } from './activity-log.controller';
import { ActivityLogService } from './activity-log.service';

// Global: qualquer serviço pode injetar ActivityLogService para auditar.
@Global()
@Module({
  imports: [PrismaModule, AccessModule],
  controllers: [ActivityLogController],
  providers: [ActivityLogService],
  exports: [ActivityLogService]
})
export class ActivityLogModule {}
