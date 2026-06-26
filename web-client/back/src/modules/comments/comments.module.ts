import { Module } from '@nestjs/common';
import { PrismaModule } from 'src/database/prisma/prisma.module';
import { AccessModule } from 'src/modules/access/access.module';

import { CommentsController } from './comments.controller';
import { CommentsService } from './comments.service';

@Module({
  imports: [PrismaModule, AccessModule],
  controllers: [CommentsController],
  providers: [CommentsService]
})
export class CommentsModule {}
