import { Module } from '@nestjs/common';
import { JwtModule } from '@nestjs/jwt';
import { PrismaModule } from 'src/database/prisma/prisma.module';
import { CreditAccountModule } from 'src/modules/credit-account/credit-account.module';

import { UserController } from './user.controller';
import { UserActivityRegistry } from './user.registry';
import { UserRepository } from './user.repository';
import { UserService } from './user.service';

@Module({
  controllers: [UserController],
  providers: [UserService, UserRepository, UserActivityRegistry],
  imports: [PrismaModule, JwtModule, CreditAccountModule],
  exports: [UserService, UserActivityRegistry]
})
export class UserModule {}
