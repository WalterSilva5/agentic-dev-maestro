import { randomBytes } from 'crypto';
import {
  BadRequestException,
  ConflictException,
  ForbiddenException,
  Injectable,
  NotFoundException
} from '@nestjs/common';
import { PrismaService } from 'src/database/prisma/prisma.service';
import { EmailService } from 'src/modules/email/email.service';
import { MembershipRole } from '@prisma/client';

import type { CreateInvitationDto } from './dto/create-invitation.dto';

const INVITE_TTL_DAYS = 7;

@Injectable()
export class InvitationsService {
  constructor(
    private prisma: PrismaService,
    private email: EmailService
  ) {}

  private frontendUrl(): string {
    return (process.env.FRONTEND_URL || 'http://localhost:4200').replace(/\/$/, '');
  }

  // OWNER/MANAGER convida alguém. Se o e-mail já tem conta, vira membro na hora.
  // Caso contrário, cria um convite com token e envia o link de aceite por e-mail.
  async invite(companyId: number, invitedByMembershipId: number, dto: CreateInvitationDto) {
    const email = dto.email.toLowerCase().trim();
    const role = dto.role ?? MembershipRole.DEV;

    const user = await this.prisma.user.findUnique({
      where: { email },
      select: { id: true, firstName: true }
    });

    if (user) {
      const existing = await this.prisma.membership.findUnique({
        where: { userId_companyId: { userId: user.id, companyId } }
      });
      if (existing) throw new ConflictException('Usuário já é membro deste workspace');

      const membership = await this.prisma.membership.create({
        data: { companyId, userId: user.id, role },
        select: {
          id: true,
          role: true,
          user: { select: { id: true, firstName: true, lastName: true, email: true } }
        }
      });

      const company = await this.prisma.company.findUnique({
        where: { id: companyId },
        select: { name: true }
      });
      void this.email
        .sendEmail(
          membership.user.email,
          `Você foi adicionado ao workspace ${company?.name ?? ''}`,
          `<p>Olá ${membership.user.firstName},</p>
           <p>Você agora é membro de <b>${company?.name ?? ''}</b> com o papel <b>${membership.role}</b>.</p>
           <p><a href="${this.frontendUrl()}">Acessar o workspace</a></p>`
        )
        .catch(() => undefined);

      return { mode: 'added' as const, membership };
    }

    // Sem conta ainda: gera convite por token e envia o link.
    await this.prisma.invitation.deleteMany({ where: { companyId, email, acceptedAt: null } });

    const token = randomBytes(24).toString('hex');
    const expiresAt = new Date(Date.now() + INVITE_TTL_DAYS * 86_400_000);
    const invitation = await this.prisma.invitation.create({
      data: { companyId, email, role, token, invitedByMembershipId, expiresAt },
      select: { id: true, email: true, role: true, expiresAt: true, createdAt: true }
    });

    const company = await this.prisma.company.findUnique({
      where: { id: companyId },
      select: { name: true }
    });
    const link = `${this.frontendUrl()}/invite/${token}`;
    void this.email
      .sendEmail(
        email,
        `Convite para o workspace ${company?.name ?? ''}`,
        `<p>Você foi convidado para o workspace <b>${company?.name ?? ''}</b> com o papel <b>${role}</b>.</p>
         <p><a href="${link}">Aceitar o convite</a> (expira em ${INVITE_TTL_DAYS} dias).</p>
         <p>Se você ainda não tem conta, poderá criar uma ao abrir o link.</p>`
      )
      .catch(() => undefined);

    return { mode: 'invited' as const, invitation, link };
  }

  // Lista os convites pendentes (não aceitos, não revogados, não expirados).
  listPending(companyId: number) {
    return this.prisma.invitation.findMany({
      where: { companyId, acceptedAt: null, revokedAt: null, expiresAt: { gt: new Date() } },
      select: { id: true, email: true, role: true, expiresAt: true, createdAt: true },
      orderBy: { createdAt: 'desc' }
    });
  }

  async revoke(companyId: number, id: number) {
    const inv = await this.prisma.invitation.findFirst({ where: { id, companyId } });
    if (!inv) throw new NotFoundException('Convite não encontrado neste workspace');
    await this.prisma.invitation.update({ where: { id }, data: { revokedAt: new Date() } });
    return { id, revoked: true };
  }

  // Público: detalhes para a tela de aceite (antes de logar/cadastrar).
  async getByToken(token: string) {
    const inv = await this.findValid(token);
    const company = await this.prisma.company.findUnique({
      where: { id: inv.companyId },
      select: { name: true }
    });
    return { email: inv.email, role: inv.role, company: company?.name ?? '', expiresAt: inv.expiresAt };
  }

  // Aceita o convite criando a Membership para o usuário logado.
  async accept(token: string, userId: number) {
    const inv = await this.findValid(token);

    const user = await this.prisma.user.findUnique({
      where: { id: userId },
      select: { email: true }
    });
    if (!user || user.email.toLowerCase() !== inv.email) {
      throw new ForbiddenException('Este convite foi enviado para outro e-mail. Entre com a conta correta.');
    }

    const existing = await this.prisma.membership.findUnique({
      where: { userId_companyId: { userId, companyId: inv.companyId } }
    });
    if (existing) {
      await this.prisma.invitation.update({ where: { id: inv.id }, data: { acceptedAt: new Date() } });
      return { companyId: inv.companyId, role: existing.role, alreadyMember: true };
    }

    const membership = await this.prisma.$transaction(async (tx) => {
      const m = await tx.membership.create({
        data: { companyId: inv.companyId, userId, role: inv.role }
      });
      await tx.invitation.update({ where: { id: inv.id }, data: { acceptedAt: new Date() } });
      return m;
    });

    return { companyId: inv.companyId, role: membership.role, alreadyMember: false };
  }

  private async findValid(token: string) {
    const inv = await this.prisma.invitation.findUnique({ where: { token } });
    if (!inv || inv.revokedAt) throw new NotFoundException('Convite inválido ou revogado');
    if (inv.acceptedAt) throw new BadRequestException('Convite já utilizado');
    if (inv.expiresAt.getTime() < Date.now()) throw new BadRequestException('Convite expirado');
    return inv;
  }
}
