import type { DefaultFilter } from 'src/filters/DefaultFilter';

import type { Paginated } from './IPaginated';

export interface IBaseRepository<Dto = any, Entity = any> {
  findFilteredAsync(filter: DefaultFilter): Promise<Paginated<Entity>>;
  updateAsync(id: number, dto: Dto): Promise<Entity>;
  findByIdAsync(id: number): Promise<Entity>;
  deleteAsync(id: number): Promise<void>;
  createAsync(dto: Dto): Promise<Entity>;
}
