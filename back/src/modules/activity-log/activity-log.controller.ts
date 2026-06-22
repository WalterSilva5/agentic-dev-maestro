import { Controller, Get, Query, UseGuards } from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import { CompanyContext } from 'src/decorators/company-context.decorator';
import { unprotected } from 'src/decorators/unprotected.decorator';
import type { ICompanyContext } from 'src/interfaces/ICompanyContext';
import { ApiAccessGuard } from 'src/modules/access/api-access.guard';

import { ActivityLogService } from './activity-log.service';

@ApiTags('activity')
@unprotected()
@UseGuards(ApiAccessGuard)
@Controller('activity')
export class ActivityLogController {
  constructor(private readonly activity: ActivityLogService) {}

  @Get()
  list(
    @CompanyContext() ctx: ICompanyContext,
    @Query('entityType') entityType?: string,
    @Query('entityId') entityId?: string,
    @Query('limit') limit?: string
  ) {
    return this.activity.list(ctx, {
      entityType,
      entityId: entityId ? Number(entityId) : undefined,
      limit: limit ? Number(limit) : undefined
    });
  }
}
