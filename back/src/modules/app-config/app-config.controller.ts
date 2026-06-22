import {
  Controller,
  Get,
  Put,
  Body,
  UseGuards,
} from '@nestjs/common';
import { ApiTags, ApiBearerAuth, ApiOkResponse } from '@nestjs/swagger';
import { AppConfigService, AppConfigDto } from './app-config.service';
import { AtGuard } from 'src/modules/auth/guards/at.guard';
import { Roles } from 'src/decorators/role.decorator';
import { Role } from 'src/enums/role.enum';

@ApiTags('App Config')
@ApiBearerAuth()
@Controller('app-config')
@UseGuards(AtGuard)
export class AppConfigController {
  constructor(private readonly configService: AppConfigService) {}

  @Get()
  @Roles(Role.ADMIN)
  @ApiOkResponse({ description: 'Lista todas as configurações da aplicação' })
  async getAll(): Promise<AppConfigDto[]> {
    return this.configService.getAll();
  }

  @Put()
  @Roles(Role.ADMIN)
  @ApiOkResponse({ description: 'Atualiza múltiplas configurações' })
  async updateMany(@Body() configs: AppConfigDto[]): Promise<{ success: boolean }> {
    await this.configService.updateMany(configs);
    return { success: true };
  }
}
