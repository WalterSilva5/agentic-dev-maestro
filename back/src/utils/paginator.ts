/* eslint-disable @typescript-eslint/no-unused-vars */
import { BadRequestException } from '@nestjs/common';
import * as DataObjectParser from 'dataobject-parser';
import { createPaginator } from 'prisma-pagination';
import type { PaginateFunction } from 'prisma-pagination';
import type { DefaultFilter } from 'src/filters/DefaultFilter';

export class Paginator {
  static async applyPagination<T>(entity: T, filter: DefaultFilter): Promise<any> {
    const paginate: PaginateFunction = createPaginator({
      perPage: filter.perPage
    });

    if (filter.orderBy && filter.orderByDirection) {
      const parser: DataObjectParser = new DataObjectParser();
      parser.set(filter.orderBy, filter.orderByDirection);
      filter.orderBy = parser.data();
    }

    try {
      return await paginate<T, unknown>(
        entity,
        {
          where: filter.where,
          orderBy: filter.orderBy
        },
        {
          page: filter.page
        }
      );
    } catch (error) {
      throw new BadRequestException('Data pagination error');
    }
  }
}
