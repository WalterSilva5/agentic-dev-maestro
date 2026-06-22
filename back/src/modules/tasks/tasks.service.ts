import {
  BadRequestException,
  Injectable,
  NotFoundException
} from '@nestjs/common';
import type { Prisma } from '@prisma/client';
import { PrismaService } from 'src/database/prisma/prisma.service';
import type { ICompanyContext } from 'src/interfaces/ICompanyContext';

import type { CreateTaskDto } from './dto/create-task.dto';
import type { MoveTaskDto } from './dto/move-task.dto';

type TaskWithProject = Prisma.TaskGetPayload<{
  include: { project: { select: { key: true } }; column: { select: { name: true } } };
}>;

const VIEW_INCLUDE = {
  project: { select: { key: true } },
  column: { select: { name: true } }
} as const;

@Injectable()
export class TasksService {
  constructor(private prisma: PrismaService) {}

  // Cria a tarefa com número sequencial por projeto (GAV-1..n) numa transação.
  async create(ctx: ICompanyContext, dto: CreateTaskDto) {
    const project = await this.prisma.project.findFirst({
      where: { id: dto.projectId, companyId: ctx.companyId }
    });
    if (!project) throw new NotFoundException('Projeto não encontrado');

    const columnId = await this.resolveColumn(project.id, dto.columnId);

    const task = await this.prisma.$transaction(async (tx) => {
      const updated = await tx.project.update({
        where: { id: project.id },
        data: { taskSeq: { increment: 1 } }
      });
      return tx.task.create({
        data: {
          companyId: ctx.companyId,
          projectId: project.id,
          columnId,
          number: updated.taskSeq,
          title: dto.title,
          description: dto.description,
          objective: dto.objective,
          acceptance: dto.acceptance,
          priority: dto.priority ?? 'MEDIUM',
          estimateMd: dto.estimateMd,
          parentId: dto.parentId,
          assigneeId: dto.assigneeId,
          rank: `${Date.now().toString(36)}`
        },
        include: VIEW_INCLUDE
      });
    });

    return this.toView(task);
  }

  async list(ctx: ICompanyContext, projectId?: number) {
    const tasks = await this.prisma.task.findMany({
      where: {
        companyId: ctx.companyId,
        deletedAt: null,
        ...(projectId ? { projectId } : {})
      },
      orderBy: [{ projectId: 'asc' }, { number: 'asc' }],
      include: VIEW_INCLUDE
    });
    return tasks.map((t) => this.toView(t));
  }

  async get(ctx: ICompanyContext, idOrCode: string) {
    return this.toView(await this.resolveTask(ctx, idOrCode));
  }

  // Move a tarefa para outra coluna (= muda o status no kanban).
  async move(ctx: ICompanyContext, idOrCode: string, dto: MoveTaskDto) {
    const task = await this.resolveTask(ctx, idOrCode);
    const column = await this.prisma.boardColumn.findFirst({
      where: { id: dto.columnId, board: { projectId: task.projectId } }
    });
    if (!column) throw new BadRequestException('Coluna inválida para o projeto da tarefa');

    const updated = await this.prisma.task.update({
      where: { id: task.id },
      data: { columnId: column.id },
      include: VIEW_INCLUDE
    });
    return this.toView(updated);
  }

  // ---- helpers ----

  private async resolveColumn(projectId: number, columnId?: number): Promise<number> {
    if (columnId) {
      const col = await this.prisma.boardColumn.findFirst({
        where: { id: columnId, board: { projectId } }
      });
      if (!col) throw new BadRequestException('Coluna inválida para o projeto');
      return col.id;
    }
    const first = await this.prisma.boardColumn.findFirst({
      where: { board: { projectId } },
      orderBy: { order: 'asc' }
    });
    if (!first) throw new BadRequestException('Projeto sem colunas');
    return first.id;
  }

  // Aceita id numérico ou código legível "GAV-42", sempre dentro da empresa.
  private async resolveTask(ctx: ICompanyContext, idOrCode: string): Promise<TaskWithProject> {
    if (/^\d+$/.test(idOrCode)) {
      const byId = await this.prisma.task.findFirst({
        where: { id: Number(idOrCode), companyId: ctx.companyId, deletedAt: null },
        include: VIEW_INCLUDE
      });
      if (byId) return byId;
    }
    const match = /^([A-Za-z0-9]+)-(\d+)$/.exec(idOrCode);
    if (match) {
      const project = await this.prisma.project.findFirst({
        where: { companyId: ctx.companyId, key: match[1].toUpperCase() }
      });
      if (project) {
        const byCode = await this.prisma.task.findFirst({
          where: { projectId: project.id, number: Number(match[2]), deletedAt: null },
          include: VIEW_INCLUDE
        });
        if (byCode) return byCode;
      }
    }
    throw new NotFoundException('Tarefa não encontrada');
  }

  private toView(task: TaskWithProject) {
    return {
      ...task,
      code: `${task.project.key}-${task.number}`,
      status: task.column.name
    };
  }
}
