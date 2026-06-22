import { Module } from '@nestjs/common';
import { PrismaModule } from 'src/database/prisma/prisma.module';
import { AccessModule } from 'src/modules/access/access.module';

import { ProjectsController } from './projects.controller';
import { ProjectsService } from './projects.service';

@Module({
  imports: [PrismaModule, AccessModule],
  controllers: [ProjectsController],
  providers: [ProjectsService]
})
export class ProjectsModule {}
