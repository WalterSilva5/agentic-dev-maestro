import {
  Body,
  Controller,
  Delete,
  Get,
  Param,
  ParseIntPipe,
  Post
} from '@nestjs/common';
import { ApiBearerAuth, ApiTags } from '@nestjs/swagger';
import { AuthenticatedUser } from 'src/decorators/authenticated-user.decorator';
import { unprotected } from 'src/decorators/unprotected.decorator';
import { CompaniesService } from 'src/modules/companies/companies.service';
import type { User } from 'src/modules/user/entities/user.entity';

import { InvitationsService } from './invitations.service';
import { CreateInvitationDto } from './dto/create-invitation.dto';

// Convites de workspace. Gestão por JWT (OWNER/MANAGER); validação do token é pública;
// aceite exige usuário logado.
@ApiTags('invitations')
@Controller()
export class InvitationsController {
  constructor(
    private readonly invitations: InvitationsService,
    private readonly companies: CompaniesService
  ) {}

  @ApiBearerAuth()
  @Post('companies/:companyId/invitations')
  async create(
    @AuthenticatedUser() user: User,
    @Param('companyId', ParseIntPipe) companyId: number,
    @Body() dto: CreateInvitationDto
  ) {
    const membership = await this.companies.assertMembership(user.id, companyId, ['OWNER', 'MANAGER']);
    return this.invitations.invite(companyId, membership.id, dto);
  }

  @ApiBearerAuth()
  @Get('companies/:companyId/invitations')
  async list(
    @AuthenticatedUser() user: User,
    @Param('companyId', ParseIntPipe) companyId: number
  ) {
    await this.companies.assertMembership(user.id, companyId, ['OWNER', 'MANAGER']);
    return this.invitations.listPending(companyId);
  }

  @ApiBearerAuth()
  @Delete('companies/:companyId/invitations/:id')
  async revoke(
    @AuthenticatedUser() user: User,
    @Param('companyId', ParseIntPipe) companyId: number,
    @Param('id', ParseIntPipe) id: number
  ) {
    await this.companies.assertMembership(user.id, companyId, ['OWNER', 'MANAGER']);
    return this.invitations.revoke(companyId, id);
  }

  // Público: a tela de aceite consulta os detalhes antes de logar/cadastrar.
  @unprotected()
  @Get('invitations/:token')
  validate(@Param('token') token: string) {
    return this.invitations.getByToken(token);
  }

  @ApiBearerAuth()
  @Post('invitations/:token/accept')
  accept(@AuthenticatedUser() user: User, @Param('token') token: string) {
    return this.invitations.accept(token, user.id);
  }
}
