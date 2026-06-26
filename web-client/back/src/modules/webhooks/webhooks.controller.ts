import {
  Body,
  Controller,
  Delete,
  Get,
  Param,
  ParseIntPipe,
  Patch,
  Post,
  UseGuards
} from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import { CompanyContext } from 'src/decorators/company-context.decorator';
import { RequireRole } from 'src/decorators/require-role.decorator';
import { unprotected } from 'src/decorators/unprotected.decorator';
import type { ICompanyContext } from 'src/interfaces/ICompanyContext';
import { ApiAccessGuard } from 'src/modules/access/api-access.guard';

import { CreateWebhookDto, UpdateWebhookDto } from './dto/create-webhook.dto';
import { WebhooksService } from './webhooks.service';

// Gerenciar webhooks é uma ação administrativa (apenas OWNER/MANAGER).
@ApiTags('webhooks')
@unprotected() // ignora o AtGuard global; o ApiAccessGuard cuida da auth
@UseGuards(ApiAccessGuard)
@RequireRole('OWNER', 'MANAGER')
@Controller('webhooks')
export class WebhooksController {
  constructor(private readonly webhooks: WebhooksService) {}

  @Post()
  create(@CompanyContext() ctx: ICompanyContext, @Body() dto: CreateWebhookDto) {
    return this.webhooks.create(ctx, dto);
  }

  @Get()
  list(@CompanyContext() ctx: ICompanyContext) {
    return this.webhooks.list(ctx);
  }

  @Patch(':id')
  update(
    @CompanyContext() ctx: ICompanyContext,
    @Param('id', ParseIntPipe) id: number,
    @Body() dto: UpdateWebhookDto
  ) {
    return this.webhooks.update(ctx, id, dto);
  }

  @Delete(':id')
  remove(@CompanyContext() ctx: ICompanyContext, @Param('id', ParseIntPipe) id: number) {
    return this.webhooks.remove(ctx, id);
  }
}
