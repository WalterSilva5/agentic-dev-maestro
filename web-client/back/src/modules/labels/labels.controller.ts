import { Body, Controller, Delete, Get, Param, ParseIntPipe, Post, UseGuards } from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import { CompanyContext } from 'src/decorators/company-context.decorator';
import { unprotected } from 'src/decorators/unprotected.decorator';
import type { ICompanyContext } from 'src/interfaces/ICompanyContext';
import { ApiAccessGuard } from 'src/modules/access/api-access.guard';

import { CreateLabelDto } from './dto/create-label.dto';
import { LabelsService } from './labels.service';

// Acessível por agente (x-api-key) ou humano (JWT + X-Company-Id).
@ApiTags('labels')
@unprotected() // ignora o AtGuard global; o ApiAccessGuard cuida da auth
@UseGuards(ApiAccessGuard)
@Controller('labels')
export class LabelsController {
  constructor(private readonly labels: LabelsService) {}

  @Post()
  create(@CompanyContext() ctx: ICompanyContext, @Body() dto: CreateLabelDto) {
    return this.labels.create(ctx, dto);
  }

  @Get()
  list(@CompanyContext() ctx: ICompanyContext) {
    return this.labels.list(ctx);
  }

  @Delete(':id')
  remove(@CompanyContext() ctx: ICompanyContext, @Param('id', ParseIntPipe) id: number) {
    return this.labels.remove(ctx, id);
  }

  @Post(':id/tasks/:taskId')
  addToTask(
    @CompanyContext() ctx: ICompanyContext,
    @Param('id', ParseIntPipe) id: number,
    @Param('taskId', ParseIntPipe) taskId: number
  ) {
    return this.labels.addToTask(ctx, id, taskId);
  }

  @Delete(':id/tasks/:taskId')
  removeFromTask(
    @CompanyContext() ctx: ICompanyContext,
    @Param('id', ParseIntPipe) id: number,
    @Param('taskId', ParseIntPipe) taskId: number
  ) {
    return this.labels.removeFromTask(ctx, id, taskId);
  }
}
