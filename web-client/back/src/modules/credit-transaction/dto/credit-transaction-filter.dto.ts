import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { TransactionType } from '@prisma/client';
import { Transform } from 'class-transformer';
import {
  IsOptional,
  IsEnum,
  IsDateString,
  IsInt,
  Min,
  Max,
  IsNumber
} from 'class-validator';

export class CreditTransactionFilterDTO {
  @ApiPropertyOptional({
    description: 'Page number for pagination',
    example: 1,
    minimum: 1
  })
  @IsOptional()
  @Transform(({ value }) => CreditTransactionFilterDTO.transformToNumber(value, 1))
  @IsInt()
  @Min(1)
  page?: number = 1;

  @ApiPropertyOptional({
    description: 'Number of items per page',
    example: 10,
    minimum: 1,
    maximum: 100
  })
  @IsOptional()
  @Transform(({ value }) => CreditTransactionFilterDTO.transformLimit(value))
  @IsInt()
  @Min(1)
  @Max(100)
  limit?: number = 10;

  @ApiPropertyOptional({
    description: 'Filter by transaction type',
    enum: TransactionType,
    example: TransactionType.PURCHASE
  })
  @IsOptional()
  @IsEnum(TransactionType)
  type?: TransactionType;

  @ApiPropertyOptional({
    description: 'Filter transactions from this date (ISO string)',
    example: '2025-01-01T00:00:00.000Z'
  })
  @IsOptional()
  @IsDateString()
  startDate?: string;

  @ApiPropertyOptional({
    description: 'Filter transactions until this date (ISO string)',
    example: '2025-12-31T23:59:59.999Z'
  })
  @IsOptional()
  @IsDateString()
  endDate?: string;

  @ApiProperty({
    description: 'Filter by user ID',
    example: 1
  })
  @Transform(({ value }) => CreditTransactionFilterDTO.transformToNumber(value, 0))
  @IsNumber()
  userId: number;

  private static transformToNumber(value: unknown, defaultValue: number): number {
    if (!value || value === '') return defaultValue;
    const str = String(value);
    const num = parseInt(str, 10);
    return isNaN(num) ? defaultValue : num;
  }

  private static transformLimit(value: unknown): number {
    if (!value || value === '') return 10;
    const str = String(value);
    const num = parseInt(str, 10);
    if (isNaN(num)) return 10;
    return Math.max(1, Math.min(num, 100));
  }
}
