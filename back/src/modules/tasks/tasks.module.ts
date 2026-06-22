import { Module } from '@nestjs/common';
import { PrismaModule } from 'src/database/prisma/prisma.module';
import { AccessModule } from 'src/modules/access/access.module';

import { TasksController } from './tasks.controller';
import { TasksService } from './tasks.service';

@Module({
  imports: [PrismaModule, AccessModule],
  controllers: [TasksController],
  providers: [TasksService]
})
export class TasksModule {}
