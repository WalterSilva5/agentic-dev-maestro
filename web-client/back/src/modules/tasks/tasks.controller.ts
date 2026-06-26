import {
  Body,
  Controller,
  Delete,
  Get,
  Headers,
  Param,
  ParseIntPipe,
  Patch,
  Post,
  Query,
  UseGuards
} from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import { CompanyContext } from 'src/decorators/company-context.decorator';
import { unprotected } from 'src/decorators/unprotected.decorator';
import type { ICompanyContext } from 'src/interfaces/ICompanyContext';
import { ApiAccessGuard } from 'src/modules/access/api-access.guard';

import { AddDependencyDto } from './dto/add-dependency.dto';
import { CreateTaskDto } from './dto/create-task.dto';
import { CreateTasksBulkDto } from './dto/create-tasks-bulk.dto';
import { MoveTaskDto } from './dto/move-task.dto';
import { UpdateTaskDto } from './dto/update-task.dto';
import { TasksService } from './tasks.service';

// Acessível por agente (x-api-key) ou humano (JWT + X-Company-Id).
@ApiTags('tasks')
@unprotected()
@UseGuards(ApiAccessGuard)
@Controller('tasks')
export class TasksController {
  constructor(private readonly tasks: TasksService) {}

  @Post()
  create(@CompanyContext() ctx: ICompanyContext, @Body() dto: CreateTaskDto) {
    return this.tasks.create(ctx, dto);
  }

  // Decompose em massa (com Idempotency-Key opcional).
  @Post('bulk')
  bulk(
    @CompanyContext() ctx: ICompanyContext,
    @Body() dto: CreateTasksBulkDto,
    @Headers('idempotency-key') idempotencyKey?: string
  ) {
    return this.tasks.bulk(ctx, dto, idempotencyKey);
  }

  // Checklist endpoints (must come before :idOrCode routes)
  @Patch('checklist/:itemId/toggle')
  toggleChecklistItem(
    @CompanyContext() ctx: ICompanyContext,
    @Param('itemId', ParseIntPipe) itemId: number
  ) {
    return this.tasks.toggleChecklistItem(ctx, itemId);
  }

  @Delete('checklist/:itemId')
  removeChecklistItem(
    @CompanyContext() ctx: ICompanyContext,
    @Param('itemId', ParseIntPipe) itemId: number
  ) {
    return this.tasks.removeChecklistItem(ctx, itemId);
  }

  @Get()
  list(
    @CompanyContext() ctx: ICompanyContext,
    @Query('projectId') projectId?: string,
    @Query('status') status?: string,
    @Query('assigneeId') assigneeId?: string,
    @Query('priority') priority?: string,
    @Query('labelId') labelId?: string,
    @Query('parentId') parentId?: string,
    @Query('search') search?: string
  ) {
    return this.tasks.list(ctx, {
      projectId: projectId ? Number(projectId) : undefined,
      status,
      assigneeId: assigneeId ? Number(assigneeId) : undefined,
      priority,
      labelId: labelId ? Number(labelId) : undefined,
      parentId: parentId ? Number(parentId) : undefined,
      search
    });
  }

  // Fluxo da tarefa (objetivo -> subtarefas -> aceite). ?format=mermaid p/ export.
  @Get(':idOrCode/flow')
  flow(
    @CompanyContext() ctx: ICompanyContext,
    @Param('idOrCode') idOrCode: string,
    @Query('format') format?: string
  ) {
    return this.tasks.getFlow(ctx, idOrCode, format);
  }

  @Post(':idOrCode/checklist')
  addChecklistItem(
    @CompanyContext() ctx: ICompanyContext,
    @Param('idOrCode') idOrCode: string,
    @Body('title') title: string
  ) {
    return this.tasks.addChecklistItem(ctx, idOrCode, title);
  }

  @Get(':idOrCode/context')
  getContext(
    @CompanyContext() ctx: ICompanyContext,
    @Param('idOrCode') idOrCode: string
  ) {
    return this.tasks.getContext(ctx, idOrCode);
  }

  @Get(':idOrCode')
  get(@CompanyContext() ctx: ICompanyContext, @Param('idOrCode') idOrCode: string) {
    return this.tasks.get(ctx, idOrCode);
  }

  @Patch(':idOrCode')
  update(
    @CompanyContext() ctx: ICompanyContext,
    @Param('idOrCode') idOrCode: string,
    @Body() dto: UpdateTaskDto
  ) {
    return this.tasks.update(ctx, idOrCode, dto);
  }

  @Delete(':idOrCode')
  remove(@CompanyContext() ctx: ICompanyContext, @Param('idOrCode') idOrCode: string) {
    return this.tasks.remove(ctx, idOrCode);
  }

  @Post(':idOrCode/move')
  move(
    @CompanyContext() ctx: ICompanyContext,
    @Param('idOrCode') idOrCode: string,
    @Body() dto: MoveTaskDto
  ) {
    return this.tasks.move(ctx, idOrCode, dto);
  }

  @Post(':idOrCode/dependencies')
  addDependency(
    @CompanyContext() ctx: ICompanyContext,
    @Param('idOrCode') idOrCode: string,
    @Body() dto: AddDependencyDto
  ) {
    return this.tasks.addDependency(ctx, idOrCode, dto.blockerCode);
  }

  @Delete(':idOrCode/dependencies/:depId')
  removeDependency(
    @CompanyContext() ctx: ICompanyContext,
    @Param('depId', ParseIntPipe) depId: number
  ) {
    return this.tasks.removeDependency(ctx, depId);
  }
}
