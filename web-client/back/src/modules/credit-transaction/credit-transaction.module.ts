import { Module } from '@nestjs/common';
import { PrismaModule } from 'src/database/prisma/prisma.module';

import { CreditTransactionController } from './credit-transaction.controller';
import { CreditTransactionService } from './credit-transaction.service';

@Module({
  controllers: [CreditTransactionController],
  providers: [CreditTransactionService],
  exports: [CreditTransactionService],
  imports: [PrismaModule]
})
export class CreditTransactionModule {}
