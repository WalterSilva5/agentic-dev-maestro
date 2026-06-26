import { ApiPropertyOptional } from '@nestjs/swagger';
import { StudyTopicStatus } from '@prisma/client';
import { IsEnum, IsNumber, IsOptional, IsString, MaxLength } from 'class-validator';

export class UpdateStudyTopicDto {
  @ApiPropertyOptional({ example: 'Ownership e Borrowing' })
  @IsOptional()
  @IsString()
  @MaxLength(200)
  title?: string;

  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  description?: string;

  @ApiPropertyOptional({ enum: StudyTopicStatus })
  @IsOptional()
  @IsEnum(StudyTopicStatus)
  status?: StudyTopicStatus;

  @ApiPropertyOptional()
  @IsOptional()
  @IsNumber()
  weight?: number;

  @ApiPropertyOptional()
  @IsOptional()
  @IsNumber()
  estimateHours?: number;

  @ApiPropertyOptional()
  @IsOptional()
  @IsNumber()
  loggedHours?: number;

  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  notes?: string;

  @ApiPropertyOptional()
  @IsOptional()
  resources?: unknown[];
}
