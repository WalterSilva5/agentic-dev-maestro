import { Module } from '@nestjs/common';
import { PrismaModule } from 'src/database/prisma/prisma.module';

import { StudyController } from './study.controller';
import { StudyService } from './study.service';

@Module({
  imports: [PrismaModule],
  controllers: [StudyController],
  providers: [StudyService]
})
export class StudyModule {}
