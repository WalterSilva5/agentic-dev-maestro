import { Injectable } from '@nestjs/common';
import { PrismaService } from 'src/database/prisma/prisma.service';
import type { ICompanyContext } from 'src/interfaces/ICompanyContext';

// Registra toda escrita relevante (humano vs. agente) para auditoria.
@Injectable()
export class ActivityLogService {
  constructor(private prisma: PrismaService) {}

  // best-effort: não bloqueia/quebra a operação principal se a auditoria falhar
  log(
    ctx: ICompanyContext,
    entityType: string,
    entityId: number,
    action: string,
    changes?: unknown
  ) {
    return this.prisma.activityLog
      .create({
        data: {
          companyId: ctx.companyId,
          actorUserId: ctx.userId,
          viaApiKeyId: ctx.viaApiKeyId,
          entityType,
          entityId,
          action,
          changes: (changes as object) ?? undefined
        }
      })
      .catch(() => undefined);
  }

  list(
    ctx: ICompanyContext,
    filter: { entityType?: string; entityId?: number; limit?: number }
  ) {
    return this.prisma.activityLog.findMany({
      where: {
        companyId: ctx.companyId,
        ...(filter.entityType ? { entityType: filter.entityType } : {}),
        ...(filter.entityId ? { entityId: filter.entityId } : {})
      },
      orderBy: { createdAt: 'desc' },
      take: Math.min(filter.limit ?? 50, 200)
    });
  }
}
