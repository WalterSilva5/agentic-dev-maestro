import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { DocType } from '@prisma/client';
import { IsEnum, IsInt, IsOptional, IsString, MaxLength } from 'class-validator';

export class CreateDocumentDto {
  @ApiProperty({ example: 'Especificação do módulo de login' })
  @IsString()
  @MaxLength(255)
  title: string;

  @ApiProperty({ example: '# Título\n\nConteúdo em markdown.', description: 'Corpo em markdown.' })
  @IsString()
  body: string;

  @ApiPropertyOptional({ enum: DocType, example: DocType.SPEC })
  @IsOptional()
  @IsEnum(DocType)
  type?: DocType;

  @ApiPropertyOptional({ example: 1, description: 'Projeto ao qual o documento pertence.' })
  @IsOptional()
  @IsInt()
  projectId?: number;

  @ApiPropertyOptional({ example: 1, description: 'Tarefa à qual o documento pertence.' })
  @IsOptional()
  @IsInt()
  taskId?: number;
}
