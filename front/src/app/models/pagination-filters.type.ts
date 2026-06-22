export interface PaginationFilters {
  page?: number;
  perPage?: number;
  search?: string;
  where?: Record<string, any>;
  orderBy?: string;
  orderByDirection?: 'asc' | 'desc';
  select?: Record<string, any>;
  categoryId?: number;
  name?: string;
}
