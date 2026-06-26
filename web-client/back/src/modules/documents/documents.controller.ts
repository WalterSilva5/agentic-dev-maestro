import {
  Body,
  Controller,
  Delete,
  Get,
  Param,
  ParseIntPipe,
  Post,
  Put,
  Query,
  Res,
  UseGuards
} from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import type { Response } from 'express';
import { CompanyContext } from 'src/decorators/company-context.decorator';
import { unprotected } from 'src/decorators/unprotected.decorator';
import type { ICompanyContext } from 'src/interfaces/ICompanyContext';
import { ApiAccessGuard } from 'src/modules/access/api-access.guard';

import { DocumentsService } from './documents.service';
import { CreateDocumentDto } from './dto/create-document.dto';
import { UpdateDocumentDto } from './dto/update-document.dto';

// Acessível por agente (x-api-key) ou humano (JWT + X-Company-Id).
@ApiTags('documents')
@unprotected() // ignora o AtGuard global; o ApiAccessGuard cuida da auth
@UseGuards(ApiAccessGuard)
@Controller('documents')
export class DocumentsController {
  constructor(private readonly documents: DocumentsService) {}

  @Post()
  create(@CompanyContext() ctx: ICompanyContext, @Body() dto: CreateDocumentDto) {
    return this.documents.create(ctx, dto);
  }

  @Get()
  list(
    @CompanyContext() ctx: ICompanyContext,
    @Query('projectId') projectId?: string,
    @Query('taskId') taskId?: string
  ) {
    return this.documents.list(ctx, {
      projectId: projectId != null ? Number(projectId) : undefined,
      taskId: taskId != null ? Number(taskId) : undefined
    });
  }

  @Get(':id')
  findOne(@CompanyContext() ctx: ICompanyContext, @Param('id', ParseIntPipe) id: number) {
    return this.documents.findOne(ctx, id);
  }

  @Put(':id')
  update(
    @CompanyContext() ctx: ICompanyContext,
    @Param('id', ParseIntPipe) id: number,
    @Body() dto: UpdateDocumentDto
  ) {
    return this.documents.update(ctx, id, dto);
  }

  @Delete(':id')
  remove(@CompanyContext() ctx: ICompanyContext, @Param('id', ParseIntPipe) id: number) {
    return this.documents.remove(ctx, id);
  }

  // Retorna o markdown bruto como text/markdown.
  @Get(':id/export')
  async export(
    @CompanyContext() ctx: ICompanyContext,
    @Param('id', ParseIntPipe) id: number,
    @Res() res: Response
  ) {
    const doc = await this.documents.findOne(ctx, id);
    res.type('text/markdown').send(doc.body);
  }
}
