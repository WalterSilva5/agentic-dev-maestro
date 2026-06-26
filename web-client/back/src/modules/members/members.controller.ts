import {
  Body,
  Controller,
  Delete,
  Get,
  Param,
  ParseIntPipe,
  Patch,
  Post
} from '@nestjs/common';
import { ApiBearerAuth, ApiTags } from '@nestjs/swagger';
import { AuthenticatedUser } from 'src/decorators/authenticated-user.decorator';
import { CompaniesService } from 'src/modules/companies/companies.service';
import type { User } from 'src/modules/user/entities/user.entity';
import { MembershipRole } from '@prisma/client';

import { MembersService } from './members.service';
import { AddMemberDto } from './dto/add-member.dto';
import { UpdateMemberRoleDto } from './dto/update-member-role.dto';

// Gestão de membros da empresa. Ação humana (JWT) — só OWNER/MANAGER (listagem para qualquer membro).
@ApiTags('members')
@ApiBearerAuth()
@Controller('companies/:companyId/members')
export class MembersController {
  constructor(
    private readonly members: MembersService,
    private readonly companies: CompaniesService
  ) {}

  @Get()
  async list(
    @AuthenticatedUser() user: User,
    @Param('companyId', ParseIntPipe) companyId: number
  ) {
    await this.companies.assertMembership(user.id, companyId);
    return this.members.list(companyId);
  }

  @Post()
  async add(
    @AuthenticatedUser() user: User,
    @Param('companyId', ParseIntPipe) companyId: number,
    @Body() dto: AddMemberDto
  ) {
    await this.companies.assertMembership(user.id, companyId, ['OWNER', 'MANAGER']);
    return this.members.add(companyId, dto);
  }

  @Patch(':membershipId')
  async updateRole(
    @AuthenticatedUser() user: User,
    @Param('companyId', ParseIntPipe) companyId: number,
    @Param('membershipId', ParseIntPipe) membershipId: number,
    @Body() dto: UpdateMemberRoleDto
  ) {
    const membership = await this.companies.assertMembership(user.id, companyId, [
      'OWNER',
      'MANAGER'
    ]);
    return this.members.updateRole(
      companyId,
      membershipId,
      dto,
      membership.role as MembershipRole
    );
  }

  @Delete(':membershipId')
  async remove(
    @AuthenticatedUser() user: User,
    @Param('companyId', ParseIntPipe) companyId: number,
    @Param('membershipId', ParseIntPipe) membershipId: number
  ) {
    await this.companies.assertMembership(user.id, companyId, ['OWNER', 'MANAGER']);
    return this.members.remove(companyId, membershipId);
  }
}
