import { Body, Controller, Get, Post } from '@nestjs/common';
import { ApiBearerAuth, ApiOkResponse, ApiTags } from '@nestjs/swagger';
import { AuthenticatedUser } from 'src/decorators/authenticated-user.decorator';
import type { User } from 'src/modules/user/entities/user.entity';

import { CompaniesService } from './companies.service';
import { CreateCompanyDto } from './dto/create-company.dto';

// Ações humanas (JWT). Protegido pelo AtGuard global.
@ApiTags('companies')
@ApiBearerAuth()
@Controller('companies')
export class CompaniesController {
  constructor(private readonly companies: CompaniesService) {}

  @Post()
  @ApiOkResponse({ description: 'Cria empresa e vincula o criador como OWNER.' })
  create(@AuthenticatedUser() user: User, @Body() dto: CreateCompanyDto) {
    return this.companies.create(user.id, dto);
  }

  @Get()
  @ApiOkResponse({ description: 'Empresas das quais o usuário é membro.' })
  list(@AuthenticatedUser() user: User) {
    return this.companies.listForUser(user.id);
  }
}
