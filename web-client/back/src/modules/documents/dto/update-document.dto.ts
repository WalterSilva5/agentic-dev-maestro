import { ApiPropertyOptional } from '@nestjs/swagger';
import { DocType } from '@prisma/client';
import { IsEnum, IsOptional, IsString, MaxLength } from 'class-validator';

export class UpdateDocumentDto {
  @ApiPropertyOptional({ example: 'Especificação revisada' })
  @IsOptional()
  @IsString()
  @MaxLength(255)
  title?: string;

  @ApiPropertyOptional({ example: '# Título\n\nConteúdo atualizado em markdown.' })
  @IsOptional()
  @IsString()
  body?: string;

  @ApiPropertyOptional({ enum: DocType, example: DocType.SPEC })
  @IsOptional()
  @IsEnum(DocType)
  type?: DocType;
}
