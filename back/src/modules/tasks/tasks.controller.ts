import {
  Body,
  Controller,
  Get,
  Param,
  Post,
  Query,
  UseGuards
} from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import { CompanyContext } from 'src/decorators/company-context.decorator';
import { unprotected } from 'src/decorators/unprotected.decorator';
import type { ICompanyContext } from 'src/interfaces/ICompanyContext';
import { ApiAccessGuard } from 'src/modules/access/api-access.guard';

import { CreateTaskDto } from './dto/create-task.dto';
import { MoveTaskDto } from './dto/move-task.dto';
import { TasksService } from './tasks.service';

// O coração do slice: agente cria e move tarefas via API key.
@ApiTags('tasks')
@unprotected() // ignora o AtGuard global; o ApiAccessGuard cuida da auth
@UseGuards(ApiAccessGuard)
@Controller('tasks')
export class TasksController {
  constructor(private readonly tasks: TasksService) {}

  @Post()
  create(@CompanyContext() ctx: ICompanyContext, @Body() dto: CreateTaskDto) {
    return this.tasks.create(ctx, dto);
  }

  @Get()
  list(
    @CompanyContext() ctx: ICompanyContext,
    @Query('projectId') projectId?: string
  ) {
    return this.tasks.list(ctx, projectId ? Number(projectId) : undefined);
  }

  @Get(':idOrCode')
  get(@CompanyContext() ctx: ICompanyContext, @Param('idOrCode') idOrCode: string) {
    return this.tasks.get(ctx, idOrCode);
  }

  @Post(':idOrCode/move')
  move(
    @CompanyContext() ctx: ICompanyContext,
    @Param('idOrCode') idOrCode: string,
    @Body() dto: MoveTaskDto
  ) {
    return this.tasks.move(ctx, idOrCode, dto);
  }
}
