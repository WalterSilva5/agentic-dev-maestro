import { ApiProperty } from '@nestjs/swagger';
import { IsBoolean } from 'class-validator';

export class StatusDto {
  @ApiProperty()
  @IsBoolean()
  status: boolean;
}
