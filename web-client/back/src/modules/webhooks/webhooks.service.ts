import { Injectable, NotFoundException } from '@nestjs/common';
import { Prisma } from '@prisma/client';
import { PrismaService } from 'src/database/prisma/prisma.service';
import type { ICompanyContext } from 'src/interfaces/ICompanyContext';
import { ActivityLogService } from 'src/modules/activity-log/activity-log.service';

import { CreateWebhookDto, UpdateWebhookDto } from './dto/create-webhook.dto';

// CRUD de webhooks, sempre escopado por ctx.companyId (multi-tenant).
@Injectable()
export class WebhooksService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly activityLog: ActivityLogService
  ) {}

  async create(ctx: ICompanyContext, dto: CreateWebhookDto) {
    const webhook = await this.prisma.webhook.create({
      data: {
        companyId: ctx.companyId,
        url: dto.url,
        secret: dto.secret ?? null,
        events: (dto.events as Prisma.InputJsonValue) ?? undefined,
        active: true
      }
    });
    this.activityLog.log(ctx, 'Webhook', webhook.id, 'created', { url: webhook.url });
    return webhook;
  }

  list(ctx: ICompanyContext) {
    return this.prisma.webhook.findMany({
      where: { companyId: ctx.companyId },
      orderBy: { createdAt: 'desc' }
    });
  }

  async update(ctx: ICompanyContext, id: number, dto: UpdateWebhookDto) {
    await this.findOwned(ctx, id);
    const webhook = await this.prisma.webhook.update({
      where: { id },
      data: {
        ...(dto.url !== undefined ? { url: dto.url } : {}),
        ...(dto.active !== undefined ? { active: dto.active } : {}),
        ...(dto.events !== undefined
          ? { events: dto.events as Prisma.InputJsonValue }
          : {})
      }
    });
    this.activityLog.log(ctx, 'Webhook', webhook.id, 'updated', dto);
    return webhook;
  }

  async remove(ctx: ICompanyContext, id: number) {
    await this.findOwned(ctx, id);
    await this.prisma.webhook.delete({ where: { id } });
    this.activityLog.log(ctx, 'Webhook', id, 'deleted');
    return { id };
  }

  private async findOwned(ctx: ICompanyContext, id: number) {
    const webhook = await this.prisma.webhook.findFirst({
      where: { id, companyId: ctx.companyId }
    });
    if (!webhook) throw new NotFoundException('Webhook não encontrado');
    return webhook;
  }
}
