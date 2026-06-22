import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { IsOptional, IsString, Matches, MaxLength } from 'class-validator';

export class CreateProjectDto {
  @ApiProperty({ example: 'GAV — Migração GeneXus' })
  @IsString()
  @MaxLength(120)
  name: string;

  @ApiProperty({ example: 'GAV', description: 'Prefixo do código das tarefas (ex.: GAV-42).' })
  @IsString()
  @Matches(/^[A-Za-z0-9]{2,20}$/, { message: 'key deve ter 2-20 caracteres alfanuméricos' })
  key: string;

  @ApiPropertyOptional({ example: 'Projeto de migração do legado.' })
  @IsOptional()
  @IsString()
  description?: string;
}
