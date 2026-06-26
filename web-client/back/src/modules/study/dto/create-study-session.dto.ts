import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { IsInt, IsOptional, IsString, Max, Min } from 'class-validator';

export class CreateStudySessionDto {
  @ApiProperty({ description: 'ID do topico de estudo' })
  @IsInt()
  topicId: number;

  @ApiProperty({ description: 'Data/hora de inicio' })
  @IsString()
  startedAt: string;

  @ApiPropertyOptional({ description: 'Data/hora de fim' })
  @IsOptional()
  @IsString()
  endedAt?: string;

  @ApiPropertyOptional({ description: 'Duracao em minutos' })
  @IsOptional()
  @IsInt()
  durationMin?: number;

  @ApiPropertyOptional({ description: 'Notas da sessao' })
  @IsOptional()
  @IsString()
  notes?: string;

  @ApiPropertyOptional({ description: 'Nivel de confianca (1-5)' })
  @IsOptional()
  @IsInt()
  @Min(1)
  @Max(5)
  confidence?: number;
}
