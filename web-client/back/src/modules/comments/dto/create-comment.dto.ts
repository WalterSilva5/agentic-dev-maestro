import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { CommentType } from '@prisma/client';
import { IsEnum, IsInt, IsOptional, IsString, MaxLength } from 'class-validator';

export class CreateCommentDto {
  @ApiProperty()
  @IsInt()
  taskId: number;

  @ApiProperty()
  @IsString()
  @MaxLength(10000)
  body: string;

  @ApiPropertyOptional({ enum: CommentType, example: CommentType.COMMENT })
  @IsOptional()
  @IsEnum(CommentType)
  type?: CommentType;
}
