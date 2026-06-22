import { Module } from '@nestjs/common';
import { AppConfigService } from './app-config.service';
import { AppConfigController } from './app-config.controller';
import { PrismaModule } from 'src/database/prisma/prisma.module';
import { UserModule } from 'src/modules/user/user.module';

@Module({
  imports: [PrismaModule, UserModule],
  controllers: [AppConfigController],
  providers: [AppConfigService],
  exports: [AppConfigService],
})
export class AppConfigModule {}
