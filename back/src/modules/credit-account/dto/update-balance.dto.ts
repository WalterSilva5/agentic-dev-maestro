import { ApiProperty } from '@nestjs/swagger';
import { Type } from 'class-transformer';
import { IsInt, IsPositive } from 'class-validator';

export class UpdateBalanceDTO {
  @ApiProperty({ description: 'ID do usuário', example: 1 })
  @Type(() => Number)
  @IsInt()
  @IsPositive()
  userId: number;

  @ApiProperty({ description: 'Valor a adicionar', example: 100 })
  @Type(() => Number)
  @IsInt({ message: 'amount must be an integer' })
  @IsPositive()
  amount: number;
}
