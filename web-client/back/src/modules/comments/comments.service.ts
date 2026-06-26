import { Injectable, NotFoundException } from '@nestjs/common';
import { PrismaService } from 'src/database/prisma/prisma.service';
import type { ICompanyContext } from 'src/interfaces/ICompanyContext';
import { ActivityLogService } from 'src/modules/activity-log/activity-log.service';

import type { CreateCommentDto } from './dto/create-comment.dto';
import type { UpdateCommentDto } from './dto/update-comment.dto';

const AUTHOR_INCLUDE = {
  author: { select: { id: true, firstName: true, lastName: true } }
} as const;

@Injectable()
export class CommentsService {
  constructor(
    private prisma: PrismaService,
    private activity: ActivityLogService
  ) {}

  // Cria um comentário numa tarefa da empresa; marca via API key quando agente.
  async create(ctx: ICompanyContext, dto: CreateCommentDto) {
    const task = await this.prisma.task.findFirst({
      where: { id: dto.taskId, companyId: ctx.companyId }
    });
    if (!task) throw new NotFoundException('Tarefa não encontrada');

    const comment = await this.prisma.comment.create({
      data: {
        companyId: ctx.companyId,
        taskId: dto.taskId,
        authorId: ctx.userId,
        viaApiKeyId: ctx.viaApiKeyId,
        body: dto.body,
        type: dto.type ?? 'COMMENT'
      },
      include: AUTHOR_INCLUDE
    });

    this.activity.log(ctx, 'Task', dto.taskId, 'commented');

    return comment;
  }

  async list(ctx: ICompanyContext, taskId: number) {
    const task = await this.prisma.task.findFirst({
      where: { id: taskId, companyId: ctx.companyId }
    });
    if (!task) throw new NotFoundException('Tarefa não encontrada');

    return this.prisma.comment.findMany({
      where: { companyId: ctx.companyId, taskId },
      orderBy: { createdAt: 'asc' },
      include: AUTHOR_INCLUDE
    });
  }

  async update(ctx: ICompanyContext, id: number, dto: UpdateCommentDto) {
    const comment = await this.prisma.comment.findFirst({
      where: { id, companyId: ctx.companyId }
    });
    if (!comment) throw new NotFoundException('Comentário não encontrado');

    const updated = await this.prisma.comment.update({
      where: { id },
      data: { body: dto.body },
      include: AUTHOR_INCLUDE
    });

    this.activity.log(ctx, 'Task', comment.taskId, 'comment_updated');
    return updated;
  }

  async remove(ctx: ICompanyContext, id: number) {
    const comment = await this.prisma.comment.findFirst({
      where: { id, companyId: ctx.companyId }
    });
    if (!comment) throw new NotFoundException('Comentário não encontrado');

    await this.prisma.comment.delete({ where: { id } });
    this.activity.log(ctx, 'Task', comment.taskId, 'comment_deleted');
    return { deleted: true };
  }
}
