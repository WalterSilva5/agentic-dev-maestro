import { Body, Controller, Delete, Get, Param, ParseIntPipe, Patch, Post, Query, UseGuards } from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import { CompanyContext } from 'src/decorators/company-context.decorator';
import { unprotected } from 'src/decorators/unprotected.decorator';
import type { ICompanyContext } from 'src/interfaces/ICompanyContext';
import { ApiAccessGuard } from 'src/modules/access/api-access.guard';

import { CommentsService } from './comments.service';
import { CreateCommentDto } from './dto/create-comment.dto';
import { UpdateCommentDto } from './dto/update-comment.dto';

// Comentários em tarefas: autor é o usuário atual; marca quando via API key (agente).
@ApiTags('comments')
@unprotected() // ignora o AtGuard global; o ApiAccessGuard cuida da auth
@UseGuards(ApiAccessGuard)
@Controller('comments')
export class CommentsController {
  constructor(private readonly comments: CommentsService) {}

  @Post()
  create(@CompanyContext() ctx: ICompanyContext, @Body() dto: CreateCommentDto) {
    return this.comments.create(ctx, dto);
  }

  @Get()
  list(@CompanyContext() ctx: ICompanyContext, @Query('taskId') taskId: string) {
    return this.comments.list(ctx, Number(taskId));
  }

  @Patch(':id')
  update(
    @CompanyContext() ctx: ICompanyContext,
    @Param('id', ParseIntPipe) id: number,
    @Body() dto: UpdateCommentDto
  ) {
    return this.comments.update(ctx, id, dto);
  }

  @Delete(':id')
  remove(@CompanyContext() ctx: ICompanyContext, @Param('id', ParseIntPipe) id: number) {
    return this.comments.remove(ctx, id);
  }
}
