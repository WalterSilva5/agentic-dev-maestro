import { ApiProperty } from '@nestjs/swagger';
import { IsInt } from 'class-validator';

export class MoveTaskDto {
  @ApiProperty({ description: 'Coluna destino (status) no quadro do projeto.' })
  @IsInt()
  columnId: number;
}
