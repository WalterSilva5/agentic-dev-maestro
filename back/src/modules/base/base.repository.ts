/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable @typescript-eslint/no-unused-vars */
import { NotImplementedException } from '@nestjs/common';
import type { DefaultFilter } from 'src/filters/DefaultFilter';
import type { IBaseRepository } from 'src/interfaces/IBaseRepository';
import type { Paginated } from 'src/interfaces/IPaginated';

import type { UserDto } from '../user/models/user.dto';

export abstract class BaseRepository<Dto = any, Entity = any>
  implements IBaseRepository<Dto, Entity>
{
  async findFilteredAsync(
    filter: DefaultFilter,
    user?: UserDto
  ): Promise<Paginated<Entity>> {
    throw new NotImplementedException();
  }
  abstract updateAsync(id: number, dto: Dto): Promise<Entity>;
  abstract findByIdAsync(id: number): Promise<Entity>;
  abstract deleteAsync(id: number): Promise<void>;
  abstract createAsync(dto: any): Promise<Entity>;
}
