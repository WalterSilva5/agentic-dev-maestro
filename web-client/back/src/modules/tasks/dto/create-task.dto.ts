import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { TaskPriority, TaskType } from '@prisma/client';
import { IsEnum, IsInt, IsNumber, IsOptional, IsString, MaxLength } from 'class-validator';

export class CreateTaskDto {
  @ApiProperty({ example: 1 })
  @IsInt()
  projectId: number;

  @ApiProperty({ example: 'Implementar login com refresh token' })
  @IsString()
  @MaxLength(255)
  title: string;

  @ApiPropertyOptional({ example: 'Detalhes em markdown.' })
  @IsOptional()
  @IsString()
  description?: string;

  @ApiPropertyOptional({ description: 'Objetivo (entrada do fluxo).' })
  @IsOptional()
  @IsString()
  objective?: string;

  @ApiPropertyOptional({ description: 'Critério de aceite (ponto de aceitação).' })
  @IsOptional()
  @IsString()
  acceptance?: string;

  @ApiPropertyOptional({ enum: TaskPriority, example: TaskPriority.MEDIUM })
  @IsOptional()
  @IsEnum(TaskPriority)
  priority?: TaskPriority;

  @ApiPropertyOptional({ example: 1.5, description: 'Estimativa em homem-dia.' })
  @IsOptional()
  @IsNumber()
  estimateMd?: number;

  @ApiPropertyOptional({ description: 'Coluna inicial; se ausente, usa a primeira do quadro.' })
  @IsOptional()
  @IsInt()
  columnId?: number;

  @ApiPropertyOptional({ description: 'Tarefa-pai (para subtarefas).' })
  @IsOptional()
  @IsInt()
  parentId?: number;

  @ApiPropertyOptional({ description: 'Usuário responsável.' })
  @IsOptional()
  @IsInt()
  assigneeId?: number;

  @ApiPropertyOptional({ enum: TaskType, example: TaskType.FEATURE })
  @IsOptional()
  @IsEnum(TaskType)
  type?: TaskType;
}
