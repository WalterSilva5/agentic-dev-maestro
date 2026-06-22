import { Module } from '@nestjs/common';
import { PrismaModule } from 'src/database/prisma/prisma.module';

import { CreditAccountController } from './credit-account.controller';
import { CreditAccountService } from './credit-account.service';

@Module({
  imports: [PrismaModule],
  providers: [CreditAccountService],
  controllers: [CreditAccountController],
  exports: [CreditAccountService]
})
export class CreditAccountModule {}
