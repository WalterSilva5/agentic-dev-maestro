import { ApiProperty } from '@nestjs/swagger';
import { IsInt, IsString, MaxLength } from 'class-validator';

export class CreateCommentDto {
  @ApiProperty()
  @IsInt()
  taskId: number;

  @ApiProperty()
  @IsString()
  @MaxLength(10000)
  body: string;
}
