import { ApiProperty } from '@nestjs/swagger';
import { IsString } from 'class-validator';

export class UpdateCommentDto {
  @ApiProperty({ example: 'Comentário atualizado.' })
  @IsString()
  body: string;
}
