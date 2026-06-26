import {
  Body,
  Controller,
  Delete,
  Get,
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

import { CreateStudyPlanDto } from './dto/create-study-plan.dto';
import { CreateStudySessionDto } from './dto/create-study-session.dto';
import { CreateStudyTopicDto } from './dto/create-study-topic.dto';
import { ReorderTopicsDto } from './dto/reorder-topics.dto';
import { UpdateStudyPlanDto } from './dto/update-study-plan.dto';
import { UpdateStudyTopicDto } from './dto/update-study-topic.dto';
import { StudyService } from './study.service';

@ApiTags('study')
@unprotected()
@UseGuards(ApiAccessGuard)
@Controller('study')
export class StudyController {
  constructor(private readonly study: StudyService) {}

  // ---- Planos ----

  @Get('plans')
  listPlans(
    @CompanyContext() ctx: ICompanyContext,
    @Query('status') status?: string,
    @Query('category') category?: string
  ) {
    return this.study.listPlans(ctx, status, category);
  }

  @Post('plans')
  createPlan(@CompanyContext() ctx: ICompanyContext, @Body() dto: CreateStudyPlanDto) {
    return this.study.createPlan(ctx, dto);
  }

  @Get('plans/:id')
  getPlan(@CompanyContext() ctx: ICompanyContext, @Param('id', ParseIntPipe) id: number) {
    return this.study.getPlan(ctx, id);
  }

  @Patch('plans/:id')
  updatePlan(
    @CompanyContext() ctx: ICompanyContext,
    @Param('id', ParseIntPipe) id: number,
    @Body() dto: UpdateStudyPlanDto
  ) {
    return this.study.updatePlan(ctx, id, dto);
  }

  @Delete('plans/:id')
  deletePlan(@CompanyContext() ctx: ICompanyContext, @Param('id', ParseIntPipe) id: number) {
    return this.study.deletePlan(ctx, id);
  }

  // ---- Topicos ----

  @Get('plans/:planId/topics')
  listTopics(
    @CompanyContext() ctx: ICompanyContext,
    @Param('planId', ParseIntPipe) planId: number
  ) {
    return this.study.listTopics(ctx, planId);
  }

  @Post('plans/:planId/topics')
  createTopic(
    @CompanyContext() ctx: ICompanyContext,
    @Param('planId', ParseIntPipe) planId: number,
    @Body() dto: CreateStudyTopicDto
  ) {
    return this.study.createTopic(ctx, planId, dto);
  }

  @Patch('topics/:id')
  updateTopic(
    @CompanyContext() ctx: ICompanyContext,
    @Param('id', ParseIntPipe) id: number,
    @Body() dto: UpdateStudyTopicDto
  ) {
    return this.study.updateTopic(ctx, id, dto);
  }

  @Delete('topics/:id')
  deleteTopic(@CompanyContext() ctx: ICompanyContext, @Param('id', ParseIntPipe) id: number) {
    return this.study.deleteTopic(ctx, id);
  }

  @Patch('plans/:planId/topics/reorder')
  reorderTopics(
    @CompanyContext() ctx: ICompanyContext,
    @Param('planId', ParseIntPipe) planId: number,
    @Body() dto: ReorderTopicsDto
  ) {
    return this.study.reorderTopics(ctx, planId, dto);
  }

  // ---- Sessoes ----

  @Post('sessions')
  createSession(@CompanyContext() ctx: ICompanyContext, @Body() dto: CreateStudySessionDto) {
    return this.study.createSession(ctx, dto);
  }

  @Get('sessions')
  listSessions(
    @CompanyContext() ctx: ICompanyContext,
    @Query('planId') planId?: string,
    @Query('date') date?: string
  ) {
    return this.study.listSessions(ctx, planId ? Number(planId) : undefined, date);
  }

  @Get('plans/:planId/sessions')
  listPlanSessions(
    @CompanyContext() ctx: ICompanyContext,
    @Param('planId', ParseIntPipe) planId: number
  ) {
    return this.study.listSessions(ctx, planId);
  }

  // ---- Stats ----

  @Get('stats')
  getStats(@CompanyContext() ctx: ICompanyContext) {
    return this.study.getStats(ctx);
  }
}
