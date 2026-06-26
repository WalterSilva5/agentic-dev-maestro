import { ApiPropertyOptional } from '@nestjs/swagger';
import { StudyCategory, StudyPlanStatus } from '@prisma/client';
import { IsEnum, IsOptional, IsString, MaxLength } from 'class-validator';

export class UpdateStudyPlanDto {
  @ApiPropertyOptional({ example: 'Aprender Rust' })
  @IsOptional()
  @IsString()
  @MaxLength(200)
  title?: string;

  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  description?: string;

  @ApiPropertyOptional({ enum: StudyCategory })
  @IsOptional()
  @IsEnum(StudyCategory)
  category?: StudyCategory;

  @ApiPropertyOptional({ enum: StudyPlanStatus })
  @IsOptional()
  @IsEnum(StudyPlanStatus)
  status?: StudyPlanStatus;

  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  startDate?: string;

  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  targetDate?: string;

  @ApiPropertyOptional()
  @IsOptional()
  resources?: unknown[];
}
