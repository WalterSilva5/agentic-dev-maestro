import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { TaskPriority } from '@prisma/client';
import { Type } from 'class-transformer';
import {
  IsArray,
  IsEnum,
  IsInt,
  IsNumber,
  IsOptional,
  IsString,
  MaxLength,
  ValidateNested
} from 'class-validator';

export class BulkSubtaskDto {
  @ApiPropertyOptional({ description: 'Apelido local p/ referenciar em dependsOn.' })
  @IsOptional()
  @IsString()
  ref?: string;

  @ApiProperty()
  @IsString()
  @MaxLength(255)
  title: string;

  @ApiPropertyOptional()
  @IsOptional()
  @IsNumber()
  estimateMd?: number;

  @ApiPropertyOptional({ type: [String], description: 'refs (deste lote) que bloqueiam esta subtarefa.' })
  @IsOptional()
  @IsArray()
  dependsOn?: string[];
}

export class BulkTaskDto {
  @ApiPropertyOptional({ description: 'Apelido local p/ referenciar em dependsOn.' })
  @IsOptional()
  @IsString()
  ref?: string;

  @ApiProperty()
  @IsString()
  @MaxLength(255)
  title: string;

  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  description?: string;

  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  objective?: string;

  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  acceptance?: string;

  @ApiPropertyOptional({ enum: TaskPriority })
  @IsOptional()
  @IsEnum(TaskPriority)
  priority?: TaskPriority;

  @ApiPropertyOptional()
  @IsOptional()
  @IsNumber()
  estimateMd?: number;

  @ApiPropertyOptional({ type: [BulkSubtaskDto] })
  @IsOptional()
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => BulkSubtaskDto)
  subtasks?: BulkSubtaskDto[];
}

export class CreateTasksBulkDto {
  @ApiProperty({ example: 1 })
  @IsInt()
  projectId: number;

  @ApiProperty({ type: [BulkTaskDto] })
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => BulkTaskDto)
  items: BulkTaskDto[];
}
