import { Module } from '@nestjs/common';
import { PrismaModule } from 'src/database/prisma/prisma.module';
import { CompaniesModule } from 'src/modules/companies/companies.module';

import { MembersController } from './members.controller';
import { MembersService } from './members.service';

@Module({
  imports: [PrismaModule, CompaniesModule],
  controllers: [MembersController],
  providers: [MembersService],
  exports: [MembersService]
})
export class MembersModule {}
