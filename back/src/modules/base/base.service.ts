/* eslint-disable @typescript-eslint/no-explicit-any */
import { Injectable, NotFoundException } from '@nestjs/common';
import type { DefaultFilter } from 'src/filters/DefaultFilter';
import { IBaseRepository } from 'src/interfaces/IBaseRepository';
import type { IBaseService } from 'src/interfaces/IBaseService';
import type { Paginated } from 'src/interfaces/IPaginated';

@Injectable()
export abstract class BaseService<Dto = any, Entity = any>
  implements IBaseService<Dto, Entity>
{
  constructor(protected repository: IBaseRepository) {}

  async createAsync(dto: Dto): Promise<Entity> {
    return this.repository.createAsync(dto);
  }

  async updateAsync(id: number, dto: Dto): Promise<Entity> {
    await this.findByIdAsync(id);
    return this.repository.updateAsync(id, dto);
  }

  async deleteAsync(id: number): Promise<void> {
    await this.findByIdAsync(id);
    await this.repository.deleteAsync(id);
  }

  async findByIdAsync(id: number): Promise<Entity> {
    const item = await this.repository.findByIdAsync(id);
    if (!item) throw new NotFoundException('Objeto não encontrado');
    return item;
  }

  async findFilteredAsync(filter: DefaultFilter): Promise<Paginated<Entity>> {
    return this.repository.findFilteredAsync(filter);
  }
}
