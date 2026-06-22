import { ApiResponseProperty } from '@nestjs/swagger';

export class CreditAccountDto {
  @ApiResponseProperty()
  id: number;

  @ApiResponseProperty()
  balance: number;

  @ApiResponseProperty()
  createdAt: Date;

  @ApiResponseProperty()
  updatedAt?: Date;
}
