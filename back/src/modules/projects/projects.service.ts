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

  async getMetrics(ctx: ICompanyContext) {
    const projects = await this.prisma.project.findMany({
      where: { companyId: ctx.companyId, deletedAt: null },
      select: { id: true, name: true, key: true }
    });

    const now = new Date();
    const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

    // All tasks for this company
    const tasks = await this.prisma.task.findMany({
      where: { companyId: ctx.companyId, deletedAt: null },
      select: {
        id: true, projectId: true, createdAt: true, updatedAt: true,
        type: true, priority: true,
        column: { select: { name: true, isDone: true } }
      }
    });

    // Activity logs for movement events (to compute lead/cycle time)
    const moveLogs = await this.prisma.activityLog.findMany({
      where: {
        companyId: ctx.companyId,
        entityType: 'Task',
        action: { in: ['moved', 'created'] },
        createdAt: { gte: thirtyDaysAgo }
      },
      orderBy: { createdAt: 'asc' },
      select: { entityId: true, action: true, changes: true, createdAt: true }
    });

    const doneTasks = tasks.filter(t => t.column.isDone);
    const totalTasks = tasks.length;

    // Completed last 7 days
    const completedLast7d = doneTasks.filter(t => t.updatedAt && t.updatedAt >= sevenDaysAgo).length;
    // Completed last 30 days
    const completedLast30d = doneTasks.filter(t => t.updatedAt && t.updatedAt >= thirtyDaysAgo).length;

    // Lead time = time from creation to done (for done tasks in last 30d)
    const leadTimes: number[] = [];
    for (const t of doneTasks) {
      if (t.updatedAt && t.updatedAt >= thirtyDaysAgo) {
        const hours = (t.updatedAt.getTime() - t.createdAt.getTime()) / (1000 * 60 * 60);
        leadTimes.push(hours);
      }
    }
    const avgLeadTimeHours = leadTimes.length ? leadTimes.reduce((a, b) => a + b, 0) / leadTimes.length : null;

    // Cycle time = time from first "moved" (out of backlog) to done
    const firstMoveMap = new Map<number, Date>();
    for (const log of moveLogs) {
      if (log.action === 'moved' && !firstMoveMap.has(log.entityId)) {
        firstMoveMap.set(log.entityId, log.createdAt);
      }
    }
    const cycleTimes: number[] = [];
    for (const t of doneTasks) {
      if (t.updatedAt && t.updatedAt >= thirtyDaysAgo) {
        const firstMove = firstMoveMap.get(t.id);
        if (firstMove) {
          const hours = (t.updatedAt.getTime() - firstMove.getTime()) / (1000 * 60 * 60);
          cycleTimes.push(hours);
        }
      }
    }
    const avgCycleTimeHours = cycleTimes.length ? cycleTimes.reduce((a, b) => a + b, 0) / cycleTimes.length : null;

    // Throughput per week (last 4 weeks)
    const weeklyThroughput: Array<{ week: string; count: number }> = [];
    for (let i = 3; i >= 0; i--) {
      const weekStart = new Date(now.getTime() - (i + 1) * 7 * 24 * 60 * 60 * 1000);
      const weekEnd = new Date(now.getTime() - i * 7 * 24 * 60 * 60 * 1000);
      const count = doneTasks.filter(t => t.updatedAt && t.updatedAt >= weekStart && t.updatedAt < weekEnd).length;
      weeklyThroughput.push({
        week: weekStart.toISOString().slice(0, 10),
        count
      });
    }

    // By type breakdown
    const byType: Record<string, { total: number; done: number }> = {};
    for (const t of tasks) {
      const type = t.type || 'FEATURE';
      if (!byType[type]) byType[type] = { total: 0, done: 0 };
      byType[type].total++;
      if (t.column.isDone) byType[type].done++;
    }

    // By priority breakdown
    const byPriority: Record<string, { total: number; done: number }> = {};
    for (const t of tasks) {
      const p = t.priority || 'MEDIUM';
      if (!byPriority[p]) byPriority[p] = { total: 0, done: 0 };
      byPriority[p].total++;
      if (t.column.isDone) byPriority[p].done++;
    }

    // Per project stats
    const perProject = projects.map(p => {
      const projectTasks = tasks.filter(t => t.projectId === p.id);
      const projectDone = projectTasks.filter(t => t.column.isDone);
      return {
        id: p.id, name: p.name, key: p.key,
        total: projectTasks.length,
        done: projectDone.length,
        percent: projectTasks.length ? Math.round((projectDone.length / projectTasks.length) * 100) : 0
      };
    });

    return {
      summary: {
        totalTasks,
        doneTasks: doneTasks.length,
        completedLast7d,
        completedLast30d,
        avgLeadTimeHours: avgLeadTimeHours ? Math.round(avgLeadTimeHours * 10) / 10 : null,
        avgCycleTimeHours: avgCycleTimeHours ? Math.round(avgCycleTimeHours * 10) / 10 : null
      },
      weeklyThroughput,
      byType,
      byPriority,
      perProject
    };
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
                column: { select: { name: true } },
                labels: { select: { id: true, name: true, color: true } },
                assignee: { select: { id: true, firstName: true, lastName: true } }
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
