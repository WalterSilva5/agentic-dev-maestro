import {
  Body,
  Controller,
  Delete,
  Get,
  Param,
  ParseIntPipe,
  Post
} from '@nestjs/common';
import { ApiBearerAuth, ApiOkResponse, ApiTags } from '@nestjs/swagger';
import { AuthenticatedUser } from 'src/decorators/authenticated-user.decorator';
import { CompaniesService } from 'src/modules/companies/companies.service';
import type { User } from 'src/modules/user/entities/user.entity';

import { ApiKeyService } from './api-key.service';
import { CreateApiKeyDto } from './dto/create-api-key.dto';

// Gestão de API keys de agentes. Ação humana (JWT) — só OWNER/MANAGER.
@ApiTags('api-keys')
@ApiBearerAuth()
@Controller('companies/:companyId/api-keys')
export class ApiKeyController {
  constructor(
    private readonly apiKeys: ApiKeyService,
    private readonly companies: CompaniesService
  ) {}

  @Post()
  @ApiOkResponse({ description: 'Cria a chave e retorna o segredo UMA única vez.' })
  async create(
    @AuthenticatedUser() user: User,
    @Param('companyId', ParseIntPipe) companyId: number,
    @Body() dto: CreateApiKeyDto
  ) {
    const membership = await this.companies.assertMembership(user.id, companyId, [
      'OWNER',
      'MANAGER'
    ]);
    return this.apiKeys.create(companyId, membership.id, dto);
  }

  @Get()
  async list(
    @AuthenticatedUser() user: User,
    @Param('companyId', ParseIntPipe) companyId: number
  ) {
    await this.companies.assertMembership(user.id, companyId, ['OWNER', 'MANAGER']);
    return this.apiKeys.list(companyId);
  }

  @Delete(':id')
  async revoke(
    @AuthenticatedUser() user: User,
    @Param('companyId', ParseIntPipe) companyId: number,
    @Param('id', ParseIntPipe) id: number
  ) {
    await this.companies.assertMembership(user.id, companyId, ['OWNER', 'MANAGER']);
    return this.apiKeys.revoke(companyId, id);
  }
}
