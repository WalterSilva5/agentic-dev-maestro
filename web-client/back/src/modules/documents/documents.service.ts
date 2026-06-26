import { BadRequestException, Injectable, NotFoundException } from '@nestjs/common';
import { PrismaService } from 'src/database/prisma/prisma.service';
import type { ICompanyContext } from 'src/interfaces/ICompanyContext';
import { ActivityLogService } from 'src/modules/activity-log/activity-log.service';

import type { CreateDocumentDto } from './dto/create-document.dto';
import type { UpdateDocumentDto } from './dto/update-document.dto';

@Injectable()
export class DocumentsService {
  constructor(
    private prisma: PrismaService,
    private activity: ActivityLogService
  ) {}

  // Cria um documento anexado a EXATAMENTE um projeto ou uma tarefa.
  async create(ctx: ICompanyContext, dto: CreateDocumentDto) {
    const hasProject = dto.projectId != null;
    const hasTask = dto.taskId != null;
    if (hasProject === hasTask) {
      throw new BadRequestException('Informe exatamente um entre projectId e taskId');
    }

    if (hasProject) {
      const project = await this.prisma.project.findFirst({
        where: { id: dto.projectId, companyId: ctx.companyId }
      });
      if (!project) throw new NotFoundException('Projeto não encontrado');
    } else {
      const task = await this.prisma.task.findFirst({
        where: { id: dto.taskId, companyId: ctx.companyId }
      });
      if (!task) throw new NotFoundException('Tarefa não encontrada');
    }

    const doc = await this.prisma.document.create({
      data: {
        companyId: ctx.companyId,
        title: dto.title,
        body: dto.body,
        type: dto.type ?? 'SPEC',
        version: 1,
        projectId: dto.projectId,
        taskId: dto.taskId
      }
    });

    this.activity.log(ctx, 'Document', doc.id, 'created');
    return doc;
  }

  list(ctx: ICompanyContext, filter: { projectId?: number; taskId?: number }) {
    return this.prisma.document.findMany({
      where: {
        companyId: ctx.companyId,
        ...(filter.projectId != null ? { projectId: filter.projectId } : {}),
        ...(filter.taskId != null ? { taskId: filter.taskId } : {})
      },
      orderBy: { updatedAt: 'desc' }
    });
  }

  async findOne(ctx: ICompanyContext, id: number) {
    const doc = await this.prisma.document.findFirst({
      where: { id, companyId: ctx.companyId }
    });
    if (!doc) throw new NotFoundException('Documento não encontrado');
    return doc;
  }

  // Atualiza title/body/type e incrementa a versão em 1.
  async update(ctx: ICompanyContext, id: number, dto: UpdateDocumentDto) {
    await this.findOne(ctx, id);

    const doc = await this.prisma.document.update({
      where: { id },
      data: {
        title: dto.title,
        body: dto.body,
        type: dto.type,
        version: { increment: 1 }
      }
    });

    this.activity.log(ctx, 'Document', doc.id, 'updated', dto);
    return doc;
  }

  async remove(ctx: ICompanyContext, id: number) {
    await this.findOne(ctx, id);
    await this.prisma.document.delete({ where: { id } });
    this.activity.log(ctx, 'Document', id, 'deleted');
    return { id };
  }
}
