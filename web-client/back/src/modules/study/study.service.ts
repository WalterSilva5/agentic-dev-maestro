import { Injectable, NotFoundException } from '@nestjs/common';
import { PrismaService } from 'src/database/prisma/prisma.service';
import type { ICompanyContext } from 'src/interfaces/ICompanyContext';

import type { CreateStudyPlanDto } from './dto/create-study-plan.dto';
import type { CreateStudySessionDto } from './dto/create-study-session.dto';
import type { CreateStudyTopicDto } from './dto/create-study-topic.dto';
import type { ReorderTopicsDto } from './dto/reorder-topics.dto';
import type { UpdateStudyPlanDto } from './dto/update-study-plan.dto';
import type { UpdateStudyTopicDto } from './dto/update-study-topic.dto';

@Injectable()
export class StudyService {
  constructor(private prisma: PrismaService) {}

  // ---- Planos ----

  async createPlan(ctx: ICompanyContext, dto: CreateStudyPlanDto) {
    const plan = await this.prisma.studyPlan.create({
      data: {
        companyId: ctx.companyId,
        userId: ctx.userId,
        title: dto.title,
        description: dto.description,
        category: dto.category,
        startDate: dto.startDate ? new Date(dto.startDate) : undefined,
        targetDate: dto.targetDate ? new Date(dto.targetDate) : undefined,
        resources: (dto.resources ?? undefined) as any
      }
    });
    return this.withProgress(plan);
  }

  async listPlans(ctx: ICompanyContext, status?: string, category?: string) {
    const plans = await this.prisma.studyPlan.findMany({
      where: {
        companyId: ctx.companyId,
        ...(status ? { status: status as any } : {}),
        ...(category ? { category: category as any } : {})
      },
      include: { topics: { orderBy: { sortOrder: 'asc' } } },
      orderBy: { updatedAt: 'desc' }
    });
    return plans.map((p) => this.withProgress(p));
  }

  async getPlan(ctx: ICompanyContext, id: number) {
    const plan = await this.prisma.studyPlan.findFirst({
      where: { id, companyId: ctx.companyId },
      include: { topics: { orderBy: { sortOrder: 'asc' } } }
    });
    if (!plan) throw new NotFoundException('Plano não encontrado');
    return this.withProgress(plan);
  }

  async updatePlan(ctx: ICompanyContext, id: number, dto: UpdateStudyPlanDto) {
    const plan = await this.prisma.studyPlan.findFirst({
      where: { id, companyId: ctx.companyId }
    });
    if (!plan) throw new NotFoundException('Plano não encontrado');
    const updated = await this.prisma.studyPlan.update({
      where: { id },
      data: {
        ...(dto.title !== undefined ? { title: dto.title } : {}),
        ...(dto.description !== undefined ? { description: dto.description } : {}),
        ...(dto.category !== undefined ? { category: dto.category } : {}),
        ...(dto.status !== undefined ? { status: dto.status } : {}),
        ...(dto.startDate !== undefined ? { startDate: new Date(dto.startDate) } : {}),
        ...(dto.targetDate !== undefined ? { targetDate: new Date(dto.targetDate) } : {}),
        ...(dto.resources !== undefined ? { resources: (dto.resources ?? undefined) as any } : {})
      },
      include: { topics: { orderBy: { sortOrder: 'asc' } } }
    });
    return this.withProgress(updated);
  }

  async deletePlan(ctx: ICompanyContext, id: number) {
    const plan = await this.prisma.studyPlan.findFirst({
      where: { id, companyId: ctx.companyId }
    });
    if (!plan) throw new NotFoundException('Plano não encontrado');
    await this.prisma.studyPlan.delete({ where: { id } });
    return { deleted: true };
  }

  // ---- Topicos ----

  async createTopic(ctx: ICompanyContext, planId: number, dto: CreateStudyTopicDto) {
    const plan = await this.prisma.studyPlan.findFirst({
      where: { id: planId, companyId: ctx.companyId }
    });
    if (!plan) throw new NotFoundException('Plano não encontrado');

    const maxOrder = await this.prisma.studyTopic.aggregate({
      where: { planId },
      _max: { sortOrder: true }
    });

    const topic = await this.prisma.studyTopic.create({
      data: {
        planId,
        parentId: dto.parentId,
        title: dto.title,
        description: dto.description,
        sortOrder: (maxOrder._max.sortOrder ?? -1) + 1,
        weight: dto.weight ?? 1,
        estimateHours: dto.estimateHours,
        resources: (dto.resources ?? undefined) as any
      }
    });
    return topic;
  }

  async listTopics(ctx: ICompanyContext, planId: number) {
    const plan = await this.prisma.studyPlan.findFirst({
      where: { id: planId, companyId: ctx.companyId }
    });
    if (!plan) throw new NotFoundException('Plano não encontrado');
    return this.prisma.studyTopic.findMany({
      where: { planId },
      orderBy: { sortOrder: 'asc' },
      include: { children: { orderBy: { sortOrder: 'asc' } } }
    });
  }

  async updateTopic(ctx: ICompanyContext, id: number, dto: UpdateStudyTopicDto) {
    const topic = await this.resolveTopic(ctx, id);
    return this.prisma.studyTopic.update({
      where: { id },
      data: {
        ...(dto.title !== undefined ? { title: dto.title } : {}),
        ...(dto.description !== undefined ? { description: dto.description } : {}),
        ...(dto.status !== undefined ? { status: dto.status } : {}),
        ...(dto.weight !== undefined ? { weight: dto.weight } : {}),
        ...(dto.estimateHours !== undefined ? { estimateHours: dto.estimateHours } : {}),
        ...(dto.loggedHours !== undefined ? { loggedHours: dto.loggedHours } : {}),
        ...(dto.notes !== undefined ? { notes: dto.notes } : {}),
        ...(dto.resources !== undefined ? { resources: (dto.resources ?? undefined) as any } : {})
      }
    });
  }

  async deleteTopic(ctx: ICompanyContext, id: number) {
    await this.resolveTopic(ctx, id);
    await this.prisma.studyTopic.delete({ where: { id } });
    return { deleted: true };
  }

  async reorderTopics(ctx: ICompanyContext, planId: number, dto: ReorderTopicsDto) {
    const plan = await this.prisma.studyPlan.findFirst({
      where: { id: planId, companyId: ctx.companyId }
    });
    if (!plan) throw new NotFoundException('Plano não encontrado');
    await this.prisma.$transaction(
      dto.ids.map((id, idx) =>
        this.prisma.studyTopic.update({ where: { id }, data: { sortOrder: idx } })
      )
    );
    return { ok: true };
  }

  // ---- Sessoes ----

  async createSession(ctx: ICompanyContext, dto: CreateStudySessionDto) {
    const topic = await this.resolveTopic(ctx, dto.topicId);
    const session = await this.prisma.studySession.create({
      data: {
        planId: topic.planId,
        topicId: dto.topicId,
        startedAt: new Date(dto.startedAt),
        endedAt: dto.endedAt ? new Date(dto.endedAt) : undefined,
        durationMin: dto.durationMin,
        notes: dto.notes,
        confidence: dto.confidence
      }
    });
    if (dto.durationMin && dto.durationMin > 0) {
      await this.prisma.studyTopic.update({
        where: { id: dto.topicId },
        data: { loggedHours: { increment: dto.durationMin / 60 } }
      });
    }
    return session;
  }

  async listSessions(ctx: ICompanyContext, planId?: number, date?: string) {
    const where: any = {
      plan: { companyId: ctx.companyId },
      ...(planId ? { planId } : {}),
      ...(date
        ? { startedAt: { gte: new Date(date), lt: new Date(date + 'T23:59:59.999Z') } }
        : {})
    };
    return this.prisma.studySession.findMany({
      where,
      include: { topic: { select: { id: true, title: true } } },
      orderBy: { startedAt: 'desc' }
    });
  }

  // ---- Stats ----

  async getStats(ctx: ICompanyContext) {
    const plans = await this.prisma.studyPlan.findMany({
      where: { companyId: ctx.companyId },
      include: { sessions: true }
    });
    const totalHours = plans.reduce(
      (sum, p) =>
        sum + p.sessions.reduce((s, ss) => s + (ss.durationMin ?? 0), 0),
      0
    ) / 60;
    const activePlans = plans.filter((p) => p.status === 'EM_ANDAMENTO').length;
    return { totalHours: Math.round(totalHours * 10) / 10, activePlans, totalPlans: plans.length };
  }

  // ---- Helpers ----

  private async resolveTopic(ctx: ICompanyContext, id: number) {
    const topic = await this.prisma.studyTopic.findFirst({
      where: { id, plan: { companyId: ctx.companyId } }
    });
    if (!topic) throw new NotFoundException('Tópico não encontrado');
    return topic;
  }

  private withProgress(plan: any) {
    const topics = plan.topics ?? [];
    const done = topics.filter((t: any) => t.status === 'CONCLUIDO');
    const notSkipped = topics.filter((t: any) => t.status !== 'PULADO');
    const doneWeight = done.reduce((s: number, t: any) => s + (t.weight ?? 1), 0);
    const totalWeight = notSkipped.reduce((s: number, t: any) => s + (t.weight ?? 1), 0);
    const progress = totalWeight > 0 ? Math.round((doneWeight / totalWeight) * 100) : 0;
    const totalTopics = notSkipped.length;
    const doneTopics = done.length;
    return { ...plan, progress, totalTopics, doneTopics };
  }
}
