import { Module } from '@nestjs/common';
import { JwtModule } from '@nestjs/jwt';
import { PrismaModule } from 'src/database/prisma/prisma.module';
import { ApiKeyModule } from 'src/modules/api-key/api-key.module';

import { ApiAccessGuard } from './api-access.guard';

// Provê o ApiAccessGuard (API key OU JWT) para os módulos de domínio.
// Reexporta os módulos das dependências do guard: como o guard é usado via
// @UseGuards no controller, o Nest o instancia no contexto do módulo do
// controller, que precisa enxergar ApiKeyService/JwtService/PrismaService.
@Module({
  imports: [PrismaModule, JwtModule.register({}), ApiKeyModule],
  providers: [ApiAccessGuard],
  exports: [ApiAccessGuard, PrismaModule, JwtModule, ApiKeyModule]
})
export class AccessModule {}
