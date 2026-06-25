import { Body, Controller, Get, Param, ParseIntPipe, Post, UseGuards } from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import { CompanyContext } from 'src/decorators/company-context.decorator';
import { unprotected } from 'src/decorators/unprotected.decorator';
import type { ICompanyContext } from 'src/interfaces/ICompanyContext';
import { ApiAccessGuard } from 'src/modules/access/api-access.guard';

import { CreateProjectDto } from './dto/create-project.dto';
import { ProjectsService } from './projects.service';

// Acessível por agente (x-api-key) ou humano (JWT + X-Company-Id).
@ApiTags('projects')
@unprotected() // ignora o AtGuard global; o ApiAccessGuard cuida da auth
@UseGuards(ApiAccessGuard)
@Controller('projects')
export class ProjectsController {
  constructor(private readonly projects: ProjectsService) {}

  @Post()
  create(@CompanyContext() ctx: ICompanyContext, @Body() dto: CreateProjectDto) {
    return this.projects.create(ctx, dto);
  }

  @Get()
  list(@CompanyContext() ctx: ICompanyContext) {
    return this.projects.list(ctx);
  }

  @Get('metrics')
  metrics(@CompanyContext() ctx: ICompanyContext) {
    return this.projects.getMetrics(ctx);
  }

  @Get(':id/board')
  board(@CompanyContext() ctx: ICompanyContext, @Param('id', ParseIntPipe) id: number) {
    return this.projects.getBoard(ctx, id);
  }
}
