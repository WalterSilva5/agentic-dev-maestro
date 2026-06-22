/* eslint-disable @typescript-eslint/no-explicit-any */
import {
  Body,
  Delete,
  Get,
  Param,
  ParseIntPipe,
  Post,
  Put,
  Query,
  Res
} from '@nestjs/common';
import { ApiBearerAuth } from '@nestjs/swagger';
import { Response } from 'express';
import { DefaultFilter } from 'src/filters/DefaultFilter';
import { IBaseService } from 'src/interfaces/IBaseService';
import type { Paginated } from 'src/interfaces/IPaginated';

@ApiBearerAuth()
export class BaseController<Dto = any> {
  constructor(protected service: IBaseService<Dto>) {}

  @Get()
  protected async getFilteredAsync(
    @Query() filter: DefaultFilter
  ): Promise<Paginated<Dto>> {
    return this.service.findFilteredAsync(filter);
  }

  @Get('/:id')
  protected async findByIdAsync(@Param('id', ParseIntPipe) id: number): Promise<any> {
    return this.service.findByIdAsync(id);
  }

  @Post()
  protected async createAsync(@Body() dto: Dto): Promise<any> {
    return this.service.createAsync(dto);
  }

  @Put('/:id')
  protected async updateAsync(
    @Param('id', ParseIntPipe) id: number,
    @Body() dto: Dto
  ): Promise<any> {
    return this.service.updateAsync(id, dto);
  }

  @Delete('/:id')
  protected async deleteAsync(
    @Res({ passthrough: true }) response: Response,

    @Param('id', ParseIntPipe) id: number
  ): Promise<void> {
    response.status(204);
    return this.service.deleteAsync(id);
  }
}
