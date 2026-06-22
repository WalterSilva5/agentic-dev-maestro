import {
  ConflictException,
  ForbiddenException,
  Injectable,
  NotFoundException
} from '@nestjs/common';
import { PrismaService } from 'src/database/prisma/prisma.service';
import { MembershipRole } from '@prisma/client';

import type { AddMemberDto } from './dto/add-member.dto';
import type { UpdateMemberRoleDto } from './dto/update-member-role.dto';

@Injectable()
export class MembersService {
  constructor(private prisma: PrismaService) {}

  // Lista os membros da empresa com dados básicos do usuário.
  list(companyId: number) {
    return this.prisma.membership.findMany({
      where: { companyId },
      select: {
        id: true,
        role: true,
        user: {
          select: { id: true, firstName: true, lastName: true, email: true }
        }
      }
    });
  }

  // Adiciona um usuário (por e-mail) já cadastrado como membro da empresa.
  async add(companyId: number, dto: AddMemberDto) {
    const user = await this.prisma.user.findUnique({
      where: { email: dto.email },
      select: { id: true }
    });
    if (!user) throw new NotFoundException('Usuário não encontrado para este e-mail');

    const existing = await this.prisma.membership.findUnique({
      where: { userId_companyId: { userId: user.id, companyId } }
    });
    if (existing) throw new ConflictException('Usuário já é membro desta empresa');

    return this.prisma.membership.create({
      data: {
        companyId,
        userId: user.id,
        role: dto.role ?? MembershipRole.DEV
      },
      select: {
        id: true,
        role: true,
        user: {
          select: { id: true, firstName: true, lastName: true, email: true }
        }
      }
    });
  }

  // Altera o papel de um membro desta empresa.
  async updateRole(
    companyId: number,
    membershipId: number,
    dto: UpdateMemberRoleDto,
    requesterRole: MembershipRole
  ) {
    const membership = await this.getScopedMembership(companyId, membershipId);

    // Só um OWNER pode mexer no papel de outro OWNER.
    if (membership.role === MembershipRole.OWNER && requesterRole !== MembershipRole.OWNER) {
      throw new ForbiddenException('Apenas um OWNER pode alterar o papel de um OWNER');
    }

    // Não permite rebaixar o último OWNER da empresa.
    if (membership.role === MembershipRole.OWNER && dto.role !== MembershipRole.OWNER) {
      await this.assertNotLastOwner(companyId);
    }

    return this.prisma.membership.update({
      where: { id: membershipId },
      data: { role: dto.role },
      select: {
        id: true,
        role: true,
        user: {
          select: { id: true, firstName: true, lastName: true, email: true }
        }
      }
    });
  }

  // Remove um membro desta empresa.
  async remove(companyId: number, membershipId: number) {
    const membership = await this.getScopedMembership(companyId, membershipId);

    if (membership.role === MembershipRole.OWNER) {
      await this.assertNotLastOwner(companyId);
    }

    await this.prisma.membership.delete({ where: { id: membershipId } });
    return { id: membershipId };
  }

  // Busca um membership garantindo que pertence à empresa (multi-tenant).
  private async getScopedMembership(companyId: number, membershipId: number) {
    const membership = await this.prisma.membership.findFirst({
      where: { id: membershipId, companyId }
    });
    if (!membership) throw new NotFoundException('Membro não encontrado nesta empresa');
    return membership;
  }

  // Impede que a empresa fique sem nenhum OWNER.
  private async assertNotLastOwner(companyId: number) {
    const owners = await this.prisma.membership.count({
      where: { companyId, role: MembershipRole.OWNER }
    });
    if (owners <= 1) {
      throw new ForbiddenException('Não é possível remover/rebaixar o último OWNER da empresa');
    }
  }
}
