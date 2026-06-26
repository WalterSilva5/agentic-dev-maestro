import { BadRequestException } from '@nestjs/common';
import * as DataObjectParser from 'dataobject-parser';
import { createPaginator } from 'prisma-pagination';
import type { DefaultFilter } from 'src/filters/DefaultFilter';

import { Paginator } from './paginator';

jest.mock('prisma-pagination', () => ({ createPaginator: jest.fn() }));

let mockPaginate: jest.Mock<
  Promise<{ items: unknown[]; total: number }>,
  [unknown, { where: unknown; orderBy: unknown }, { page: number }]
>;
const mockResult: { items: unknown[]; total: number } = { items: [], total: 0 };

describe('Paginator.applyPagination without orderBy', () => {
  beforeEach(() => {
    mockPaginate = jest.fn().mockResolvedValue(mockResult);
    (createPaginator as jest.Mock).mockReturnValue(mockPaginate);
    jest.clearAllMocks();
  });

  it('paginates entity with default options', async () => {
    const filter: DefaultFilter = {
      perPage: 5,
      page: 1,
      where: { foo: 'bar' }
    };
    const result: unknown = await Paginator.applyPagination('entity', filter);

    expect(createPaginator).toHaveBeenCalledWith({ perPage: 5 });
    expect(mockPaginate).toHaveBeenCalledWith(
      'entity',
      { where: filter.where, orderBy: undefined },
      { page: 1 }
    );
    expect(result).toBe(mockResult);
  });
});

describe('Paginator.applyPagination with orderBy', () => {
  beforeEach(() => {
    mockPaginate = jest.fn().mockResolvedValue(mockResult);
    (createPaginator as jest.Mock).mockReturnValue(mockPaginate);
    jest.clearAllMocks();
  });

  it('parses and applies orderBy', async () => {
    const filter: DefaultFilter = {
      perPage: 2,
      page: 3,
      where: {},
      orderBy: 'field',
      orderByDirection: 'desc'
    };
    const parsed: unknown = { field: 'desc' };
    const setSpy = jest.spyOn(DataObjectParser.prototype, 'set');
    const dataSpy = jest
      .spyOn(DataObjectParser.prototype, 'data')
      .mockReturnValue(parsed);

    await Paginator.applyPagination('entity', filter);

    expect(setSpy).toHaveBeenCalledWith('field', 'desc');
    expect(dataSpy).toHaveBeenCalled();
    expect(createPaginator).toHaveBeenCalledWith({ perPage: 2 });
    expect(mockPaginate).toHaveBeenCalledWith(
      'entity',
      { where: filter.where, orderBy: parsed },
      { page: 3 }
    );
  });
});

describe('Paginator.applyPagination error handling', () => {
  beforeEach(() => {
    mockPaginate = jest.fn().mockRejectedValue(new Error('fail'));
    (createPaginator as jest.Mock).mockReturnValue(mockPaginate);
    jest.clearAllMocks();
  });

  it('throws BadRequestException when pagination fails', async () => {
    const filter: DefaultFilter = { perPage: 1, page: 1, where: {} };
    await expect(Paginator.applyPagination('entity', filter)).rejects.toBeInstanceOf(
      BadRequestException
    );
  });
});
