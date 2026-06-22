import { BullModule } from '@nestjs/bull';
import { Module, Global } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';

import { EmailProcessor, EMAIL_QUEUE } from './email.processor';
import { EmailQueue } from './email.queue';
import { EmailService } from './email.service';

@Global()
@Module({
  imports: [ConfigModule, BullModule.registerQueue({ name: EMAIL_QUEUE })],
  providers: [EmailService, EmailProcessor, EmailQueue],
  exports: [EmailService, EmailQueue],
})
export class EmailModule {}
