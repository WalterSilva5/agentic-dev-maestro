import { ApiProperty } from '@nestjs/swagger';
import { IsArray, IsInt } from 'class-validator';

export class ReorderTopicsDto {
  @ApiProperty({ example: [3, 1, 2], description: 'Array de IDs dos topicos na nova ordem' })
  @IsArray()
  @IsInt({ each: true })
  ids: number[];
}
