import type { DefaultFilter } from 'src/filters/DefaultFilter';
import type { UserDto } from 'src/modules/user/models/user.dto';

import type { Paginated } from './IPaginated';

export interface IBaseService<Dto = any, Entity = any> {
  findFilteredAsync(filter: DefaultFilter, user?: UserDto): Promise<Paginated<Entity>>;
  updateAsync(id: number, dto: Dto, user?: UserDto): Promise<Entity>;
  findByIdAsync(id: number, user?: UserDto): Promise<Entity>;
  deleteAsync(id: number, user?: UserDto): Promise<void>;
  createAsync(dto: Dto, user?: UserDto): Promise<Entity>;
}
