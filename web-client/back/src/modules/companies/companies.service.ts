import { ForbiddenException, Injectable } from '@nestjs/common';
import { PrismaService } from 'src/database/prisma/prisma.service';

import type { CreateCompanyDto } from './dto/create-company.dto';

function slugify(value: string): string {
  return value
    .normalize('NFD') // separa letra-base de acento
    .replace(/[^\x00-\x7F]/g, '') // remove os acentos (combining marks)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '');
}

@Injectable()
export class CompaniesService {
  constructor(private prisma: PrismaService) {}

  // Cria a empresa e vincula quem criou como OWNER.
  async create(userId: number, dto: CreateCompanyDto) {
    const slug = slugify(dto.slug ?? dto.name);
    return this.prisma.company.create({
      data: {
        name: dto.name,
        slug,
        memberships: { create: { userId, role: 'OWNER' } }
      },
      include: { memberships: true }
    });
  }

  listForUser(userId: number) {
    return this.prisma.company.findMany({
      where: { deletedAt: null, memberships: { some: { userId } } },
      include: { memberships: { where: { userId }, select: { role: true } } }
    });
  }

  // Garante que o usuário pertence à empresa (e, opcionalmente, tem um dos papéis).
  async assertMembership(userId: number, companyId: number, roles?: string[]) {
    const membership = await this.prisma.membership.findUnique({
      where: { userId_companyId: { userId, companyId } }
    });
    if (!membership) throw new ForbiddenException('Você não pertence a esta empresa');
    if (roles && !roles.includes(membership.role)) {
      throw new ForbiddenException('Permissão insuficiente para esta ação');
    }
    return membership;
  }
}
