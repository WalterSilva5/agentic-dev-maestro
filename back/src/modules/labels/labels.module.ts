import { Module } from '@nestjs/common';
import { PrismaModule } from 'src/database/prisma/prisma.module';
import { AccessModule } from 'src/modules/access/access.module';

import { LabelsController } from './labels.controller';
import { LabelsService } from './labels.service';

@Module({
  imports: [PrismaModule, AccessModule],
  controllers: [LabelsController],
  providers: [LabelsService]
})
export class LabelsModule {}
