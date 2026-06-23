import { Injectable, NotFoundException } from '@nestjs/common';
import { PrismaService } from 'src/database/prisma/prisma.service';
import type { ICompanyContext } from 'src/interfaces/ICompanyContext';

import type { CreateProjectDto } from './dto/create-project.dto';

// Colunas padrão criadas junto com o quadro de um projeto novo.
const DEFAULT_COLUMNS = [
  { name: 'Backlog', order: 0 },
  { name: 'A fazer', order: 1 },
  { name: 'Fazendo', order: 2 },
  { name: 'Revisão', order: 3 },
  { name: 'Concluído', order: 4, isDone: true }
];

@Injectable()
export class ProjectsService {
  constructor(private prisma: PrismaService) {}

  // Cria o projeto + quadro "Principal" + colunas padrão.
  create(ctx: ICompanyContext, dto: CreateProjectDto) {
    return this.prisma.project.create({
      data: {
        companyId: ctx.companyId,
        name: dto.name,
        key: dto.key.toUpperCase(),
        description: dto.description,
        boards: {
          create: { name: 'Principal', columns: { create: DEFAULT_COLUMNS } }
        }
      },
      include: { boards: { include: { columns: { orderBy: { order: 'asc' } } } } }
    });
  }

  list(ctx: ICompanyContext) {
    return this.prisma.project.findMany({
      where: { companyId: ctx.companyId, deletedAt: null },
      orderBy: { createdAt: 'asc' }
    });
  }

  // Quadro completo (colunas + tarefas) para renderizar o kanban.
  async getBoard(ctx: ICompanyContext, projectId: number) {
    const board = await this.prisma.board.findFirst({
      where: { projectId, project: { companyId: ctx.companyId } },
      include: {
        columns: {
          orderBy: { order: 'asc' },
          include: {
            tasks: {
              where: { deletedAt: null },
              orderBy: { rank: 'asc' },
              include: {
                project: { select: { key: true } },
                column: { select: { name: true } }
              }
            }
          }
        }
      }
    });
    if (!board) throw new NotFoundException('Quadro não encontrado');

    // Adiciona campos computados code e status (mesmo pattern de TasksService.toView).
    for (const col of board.columns) {
      for (const task of col.tasks) {
        (task as Record<string, unknown>).code = `${(task as any).project.key}-${task.number}`;
        (task as Record<string, unknown>).status = (task as any).column.name;
      }
    }

    return board;
  }
}
