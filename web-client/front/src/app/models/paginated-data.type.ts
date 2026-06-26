import { Meta } from './meta.type';

export class PaginatedData<T> {
  data: T[] = [];
  meta: Meta = new Meta();
}

export default PaginatedData;
