import { ApiPropertyOptional } from '@nestjs/swagger';
import { IsOptional } from 'class-validator';

export class DefaultFilter {
  @IsOptional()
  @ApiPropertyOptional()
  page?: number = 1;

  @IsOptional()
  @ApiPropertyOptional()
  perPage?: number = 10;

  @IsOptional()
  @ApiPropertyOptional()
  search?: string;

  @IsOptional()
  @ApiPropertyOptional()
  where?: Record<string, any>;

  @IsOptional()
  @ApiPropertyOptional()
  orderBy?: string = 'id';

  @IsOptional()
  @ApiPropertyOptional()
  orderByDirection?: 'asc' | 'desc' = 'desc';

  select?: Record<string, any> = {};
}
