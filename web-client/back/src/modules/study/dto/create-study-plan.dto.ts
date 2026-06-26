import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { StudyCategory } from '@prisma/client';
import { IsEnum, IsOptional, IsString, MaxLength } from 'class-validator';

export class CreateStudyPlanDto {
  @ApiProperty({ example: 'Aprender Rust' })
  @IsString()
  @MaxLength(200)
  title: string;

  @ApiPropertyOptional({ example: 'Roadmap completo de Rust' })
  @IsOptional()
  @IsString()
  description?: string;

  @ApiProperty({ enum: StudyCategory, example: StudyCategory.LINGUAGEM })
  @IsEnum(StudyCategory)
  category: StudyCategory;

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
