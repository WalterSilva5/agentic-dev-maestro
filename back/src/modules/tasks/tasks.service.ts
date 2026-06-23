import {
  BadRequestException,
  ConflictException,
  Injectable,
  NotFoundException
} from '@nestjs/common';
import type { Prisma } from '@prisma/client';
import { PrismaService } from 'src/database/prisma/prisma.service';
import type { ICompanyContext } from 'src/interfaces/ICompanyContext';
import { ActivityLogService } from 'src/modules/activity-log/activity-log.service';
import { IdempotencyService } from 'src/modules/idempotency/idempotency.service';
import { WebhookDispatchService } from 'src/modules/webhooks/webhook-dispatch.service';

import type { CreateTaskDto } from './dto/create-task.dto';
import type { CreateTasksBulkDto } from './dto/create-tasks-bulk.dto';
import type { MoveTaskDto } from './dto/move-task.dto';
import type { UpdateTaskDto } from './dto/update-task.dto';

type TaskWithProject = Prisma.TaskGetPayload<{
  include: { project: { select: { key: true } }; column: { select: { name: true } } };
}>;

const VIEW_INCLUDE = {
  project: { select: { key: true } },
  column: { select: { name: true } },
  labels: { select: { id: true, name: true, color: true } },
  assignee: { select: { id: true, firstName: true, lastName: true } }
} as const;

export interface TaskListFilter {
  projectId?: number;
  status?: string; // nome da coluna
  assigneeId?: number;
  priority?: string;
  labelId?: number;
  parentId?: number;
  search?: string;
}

@Injectable()
export class TasksService {
  constructor(
    private prisma: PrismaService,
    private activity: ActivityLogService,
    private idempotency: IdempotencyService,
    private webhooks: WebhookDispatchService
  ) {}

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

    const view = this.toView(task);
    this.activity.log(ctx, 'Task', task.id, 'created');
    void this.webhooks.dispatch(ctx.companyId, 'task.created', view);
    return view;
  }

  async list(ctx: ICompanyContext, filter: TaskListFilter) {
    const where: Prisma.TaskWhereInput = {
      companyId: ctx.companyId,
      deletedAt: null,
      ...(filter.projectId ? { projectId: filter.projectId } : {}),
      ...(filter.assigneeId ? { assigneeId: filter.assigneeId } : {}),
      ...(filter.priority ? { priority: filter.priority as Prisma.EnumTaskPriorityFilter } : {}),
      ...(filter.status ? { column: { name: filter.status } } : {}),
      ...(filter.labelId ? { labels: { some: { id: filter.labelId } } } : {}),
      ...(filter.parentId !== undefined ? { parentId: filter.parentId } : {}),
      ...(filter.search ? { title: { contains: filter.search } } : {})
    };
    const tasks = await this.prisma.task.findMany({
      where,
      orderBy: [{ projectId: 'asc' }, { number: 'asc' }],
      include: VIEW_INCLUDE
    });
    return tasks.map((t) => this.toView(t));
  }

  async get(ctx: ICompanyContext, idOrCode: string) {
    return this.toView(await this.resolveTask(ctx, idOrCode));
  }

  async update(ctx: ICompanyContext, idOrCode: string, dto: UpdateTaskDto) {
    const task = await this.resolveTask(ctx, idOrCode);
    const updated = await this.prisma.task.update({
      where: { id: task.id },
      data: {
        ...(dto.title !== undefined ? { title: dto.title } : {}),
        ...(dto.description !== undefined ? { description: dto.description } : {}),
        ...(dto.objective !== undefined ? { objective: dto.objective } : {}),
        ...(dto.acceptance !== undefined ? { acceptance: dto.acceptance } : {}),
        ...(dto.priority !== undefined ? { priority: dto.priority } : {}),
        ...(dto.estimateMd !== undefined ? { estimateMd: dto.estimateMd } : {}),
        ...(dto.assigneeId !== undefined ? { assigneeId: dto.assigneeId } : {})
      },
      include: VIEW_INCLUDE
    });
    const view = this.toView(updated);
    this.activity.log(ctx, 'Task', task.id, 'updated');
    void this.webhooks.dispatch(ctx.companyId, 'task.updated', view);
    return view;
  }

  async remove(ctx: ICompanyContext, idOrCode: string) {
    const task = await this.resolveTask(ctx, idOrCode);
    await this.prisma.task.update({
      where: { id: task.id },
      data: { deletedAt: new Date() }
    });
    this.activity.log(ctx, 'Task', task.id, 'deleted');
    void this.webhooks.dispatch(ctx.companyId, 'task.deleted', {
      id: task.id,
      code: `${task.project.key}-${task.number}`
    });
    return { deleted: true };
  }

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
    const view = this.toView(updated);
    this.activity.log(ctx, 'Task', task.id, 'moved', {
      from: task.column.name,
      to: column.name
    });
    void this.webhooks.dispatch(ctx.companyId, 'task.moved', view);
    return view;
  }

  // Criação em massa (decompose): tarefas + subtarefas + arestas dependsOn,
  // tudo em uma transação e protegido por Idempotency-Key.
  async bulk(ctx: ICompanyContext, dto: CreateTasksBulkDto, idempotencyKey?: string) {
    return this.idempotency.run(ctx.companyId, idempotencyKey, async () => {
      const ids = await this.prisma.$transaction(async (tx) => {
        const project = await tx.project.findFirst({
          where: { id: dto.projectId, companyId: ctx.companyId }
        });
        if (!project) throw new NotFoundException('Projeto não encontrado');
        const firstCol = await tx.boardColumn.findFirst({
          where: { board: { projectId: project.id } },
          orderBy: { order: 'asc' }
        });
        if (!firstCol) throw new BadRequestException('Projeto sem colunas');

        const refMap = new Map<string, number>();
        const created: number[] = [];
        const pending: Array<{ ref?: string; dependsOn?: string[] }> = [];

        const createOne = async (
          item: {
            ref?: string;
            title: string;
            description?: string;
            objective?: string;
            acceptance?: string;
            priority?: string;
            estimateMd?: number;
          },
          parentId?: number
        ) => {
          const updated = await tx.project.update({
            where: { id: project.id },
            data: { taskSeq: { increment: 1 } }
          });
          const t = await tx.task.create({
            data: {
              companyId: ctx.companyId,
              projectId: project.id,
              columnId: firstCol.id,
              number: updated.taskSeq,
              title: item.title,
              description: item.description,
              objective: item.objective,
              acceptance: item.acceptance,
              priority: (item.priority as Prisma.TaskCreateInput['priority']) ?? 'MEDIUM',
              estimateMd: item.estimateMd,
              parentId,
              rank: `${Date.now().toString(36)}-${updated.taskSeq}`
            }
          });
          if (item.ref) refMap.set(item.ref, t.id);
          created.push(t.id);
          return t;
        };

        for (const item of dto.items) {
          const parent = await createOne(item);
          pending.push({ ref: item.ref });
          for (const sub of item.subtasks ?? []) {
            await createOne(sub, parent.id);
            pending.push({ ref: sub.ref, dependsOn: sub.dependsOn });
          }
        }

        // resolve dependsOn -> arestas de precedência
        for (const p of pending) {
          if (!p.ref || !p.dependsOn) continue;
          const blockedId = refMap.get(p.ref);
          if (!blockedId) continue;
          for (const depRef of p.dependsOn) {
            const blockerId = refMap.get(depRef);
            if (blockerId && blockerId !== blockedId) {
              await tx.taskDependency
                .create({ data: { companyId: ctx.companyId, blockerId, blockedId } })
                .catch(() => undefined);
            }
          }
        }
        return created;
      });

      const tasks = await this.prisma.task.findMany({
        where: { id: { in: ids } },
        include: VIEW_INCLUDE,
        orderBy: { number: 'asc' }
      });
      this.activity.log(ctx, 'Project', dto.projectId, 'bulk_tasks_created', {
        count: ids.length
      });
      return tasks.map((t) => this.toView(t));
    });
  }

  // ---- dependências e fluxo (doc 08) ----

  async addDependency(ctx: ICompanyContext, idOrCode: string, blockerCode: string) {
    const blocked = await this.resolveTask(ctx, idOrCode);
    const blocker = await this.resolveTask(ctx, blockerCode);
    if (blocker.id === blocked.id) {
      throw new BadRequestException('Uma tarefa não pode depender de si mesma');
    }
    if (await this.wouldCycle(ctx.companyId, blocker.id, blocked.id)) {
      throw new BadRequestException('Dependência criaria um ciclo (o fluxo deve ser acíclico)');
    }
    try {
      await this.prisma.taskDependency.create({
        data: { companyId: ctx.companyId, blockerId: blocker.id, blockedId: blocked.id }
      });
    } catch {
      throw new ConflictException('Dependência já existe');
    }
    this.activity.log(ctx, 'Task', blocked.id, 'dependency_added', {
      blocker: `${blocker.project.key}-${blocker.number}`
    });
    return { blocker: blockerCode, blocked: idOrCode };
  }

  async removeDependency(ctx: ICompanyContext, depId: number) {
    const dep = await this.prisma.taskDependency.findFirst({
      where: { id: depId, companyId: ctx.companyId }
    });
    if (!dep) throw new NotFoundException('Dependência não encontrada');
    await this.prisma.taskDependency.delete({ where: { id: depId } });
    this.activity.log(ctx, 'Task', dep.blockedId, 'dependency_removed');
    return { removed: true };
  }

  // Monta o grafo do fluxo: objetivo -> subtarefas (com dependências) -> aceite.
  async getFlow(ctx: ICompanyContext, idOrCode: string, format?: string) {
    const parent = await this.resolveTask(ctx, idOrCode);
    const subtasks = await this.prisma.task.findMany({
      where: { parentId: parent.id, deletedAt: null },
      include: { column: { select: { name: true, isDone: true } }, project: { select: { key: true } } },
      orderBy: { number: 'asc' }
    });
    const ids = subtasks.map((s) => s.id);
    const deps = ids.length
      ? await this.prisma.taskDependency.findMany({
          where: { companyId: ctx.companyId, blockerId: { in: ids }, blockedId: { in: ids } }
        })
      : [];

    const doneSet = new Set(subtasks.filter((s) => s.column.isDone).map((s) => s.id));
    const blockersOf = new Map<number, number[]>();
    const hasIncoming = new Set<number>();
    const hasOutgoing = new Set<number>();
    for (const d of deps) {
      hasIncoming.add(d.blockedId);
      hasOutgoing.add(d.blockerId);
      const arr = blockersOf.get(d.blockedId) ?? [];
      arr.push(d.blockerId);
      blockersOf.set(d.blockedId, arr);
    }

    const nodes: Array<Record<string, unknown>> = [
      { id: 'objetivo', kind: 'entry', label: parent.objective || 'Objetivo' }
    ];
    for (const s of subtasks) {
      const blockers = blockersOf.get(s.id) ?? [];
      const blocked = blockers.some((b) => !doneSet.has(b));
      let state: string;
      if (s.column.isDone) state = 'done';
      else if (blocked) state = 'blocked';
      else state = ['backlog', 'a fazer'].includes(s.column.name.toLowerCase()) ? 'todo' : 'doing';
      nodes.push({
        id: `t${s.id}`,
        code: `${s.project.key}-${s.number}`,
        title: s.title,
        status: s.column.name,
        state
      });
    }
    nodes.push({ id: 'aceite', kind: 'exit', label: parent.acceptance || 'Aceite' });

    const edges = deps.map((d) => ({ from: `t${d.blockerId}`, to: `t${d.blockedId}` }));
    if (subtasks.length === 0) {
      edges.push({ from: 'objetivo', to: 'aceite' });
    } else {
      for (const s of subtasks) if (!hasIncoming.has(s.id)) edges.push({ from: 'objetivo', to: `t${s.id}` });
      for (const s of subtasks) if (!hasOutgoing.has(s.id)) edges.push({ from: `t${s.id}`, to: 'aceite' });
    }

    const flow = {
      task: {
        code: `${parent.project.key}-${parent.number}`,
        title: parent.title,
        objective: parent.objective,
        acceptance: parent.acceptance
      },
      progress: { done: doneSet.size, total: subtasks.length },
      nodes,
      edges
    };
    return format === 'mermaid' ? { mermaid: this.toMermaid(flow) } : flow;
  }

  // ---- helpers ----

  private toMermaid(flow: {
    nodes: Array<Record<string, unknown>>;
    edges: Array<{ from: string; to: string }>;
  }): string {
    const esc = (s: unknown) => String(s ?? '').replace(/"/g, "'");
    const lines = ['flowchart TD'];
    for (const n of flow.nodes) {
      if (n.kind === 'entry' || n.kind === 'exit') {
        lines.push(`  ${n.id}(["${esc(n.label)}"])`);
      } else {
        lines.push(`  ${n.id}["${esc(n.code)}: ${esc(n.title)}"]`);
      }
    }
    for (const e of flow.edges) lines.push(`  ${e.from} --> ${e.to}`);
    return lines.join('\n');
  }

  // Detecta se adicionar blocker->blocked fecharia um ciclo (já existe caminho
  // blocked ->...-> blocker seguindo as arestas atuais).
  private async wouldCycle(companyId: number, blockerId: number, blockedId: number): Promise<boolean> {
    const deps = await this.prisma.taskDependency.findMany({
      where: { companyId },
      select: { blockerId: true, blockedId: true }
    });
    const adj = new Map<number, number[]>();
    for (const d of deps) {
      const arr = adj.get(d.blockerId) ?? [];
      arr.push(d.blockedId);
      adj.set(d.blockerId, arr);
    }
    const stack = [blockedId];
    const seen = new Set<number>();
    while (stack.length) {
      const cur = stack.pop() as number;
      if (cur === blockerId) return true;
      if (seen.has(cur)) continue;
      seen.add(cur);
      for (const next of adj.get(cur) ?? []) stack.push(next);
    }
    return false;
  }

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
