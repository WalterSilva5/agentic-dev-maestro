import { ConflictException, Injectable, NotFoundException } from '@nestjs/common';
import { Prisma } from '@prisma/client';
import { PrismaService } from 'src/database/prisma/prisma.service';
import type { ICompanyContext } from 'src/interfaces/ICompanyContext';
import { ActivityLogService } from 'src/modules/activity-log/activity-log.service';

import type { CreateLabelDto } from './dto/create-label.dto';

@Injectable()
export class LabelsService {
  constructor(
    private prisma: PrismaService,
    private activity: ActivityLogService
  ) {}

  // Cria etiqueta para a empresa do contexto; unicidade por (companyId, name).
  async create(ctx: ICompanyContext, dto: CreateLabelDto) {
    try {
      const label = await this.prisma.label.create({
        data: {
          companyId: ctx.companyId,
          name: dto.name,
          color: dto.color
        }
      });
      this.activity.log(ctx, 'Label', label.id, 'created');
      return label;
    } catch (e) {
      if (e instanceof Prisma.PrismaClientKnownRequestError && e.code === 'P2002') {
        throw new ConflictException('Já existe uma etiqueta com este nome nesta empresa');
      }
      throw e;
    }
  }

  list(ctx: ICompanyContext) {
    return this.prisma.label.findMany({
      where: { companyId: ctx.companyId },
      orderBy: { name: 'asc' }
    });
  }

  async remove(ctx: ICompanyContext, id: number) {
    const label = await this.prisma.label.findFirst({
      where: { id, companyId: ctx.companyId }
    });
    if (!label) throw new NotFoundException('Etiqueta não encontrada');
    return this.prisma.label.delete({ where: { id: label.id } });
  }

  async addToTask(ctx: ICompanyContext, id: number, taskId: number) {
    await this.assertLabel(ctx, id);
    await this.assertTask(ctx, taskId);
    const task = await this.prisma.task.update({
      where: { id: taskId },
      data: { labels: { connect: { id } } }
    });
    this.activity.log(ctx, 'Task', taskId, 'label_added');
    return task;
  }

  async removeFromTask(ctx: ICompanyContext, id: number, taskId: number) {
    await this.assertLabel(ctx, id);
    await this.assertTask(ctx, taskId);
    const task = await this.prisma.task.update({
      where: { id: taskId },
      data: { labels: { disconnect: { id } } }
    });
    this.activity.log(ctx, 'Task', taskId, 'label_removed');
    return task;
  }

  // Garante que a etiqueta pertence à empresa do contexto.
  private async assertLabel(ctx: ICompanyContext, id: number) {
    const label = await this.prisma.label.findFirst({
      where: { id, companyId: ctx.companyId }
    });
    if (!label) throw new NotFoundException('Etiqueta não encontrada');
    return label;
  }

  // Garante que a task pertence à empresa do contexto.
  private async assertTask(ctx: ICompanyContext, taskId: number) {
    const task = await this.prisma.task.findFirst({
      where: { id: taskId, companyId: ctx.companyId }
    });
    if (!task) throw new NotFoundException('Tarefa não encontrada');
    return task;
  }
}
