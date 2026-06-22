import { Controller, Get } from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import { unprotected } from 'src/decorators/unprotected.decorator';
import { RoutesEnum } from 'src/enums/routes.enum';

import { HealthService } from './health.service';

@ApiTags(RoutesEnum.HEALTH)
@Controller(RoutesEnum.HEALTH)
export class HealthController {
  constructor(private readonly healthService: HealthService) {}

  @Get()
  @unprotected()
  protected async getStatus(): Promise<any> {
    return this.healthService.getStatus();
  }
}
