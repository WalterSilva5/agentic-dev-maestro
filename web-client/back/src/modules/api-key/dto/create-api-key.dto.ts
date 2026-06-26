import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { IsArray, IsDateString, IsOptional, IsString } from 'class-validator';

export class CreateApiKeyDto {
  @ApiProperty({ example: 'agente claude-code' })
  @IsString()
  label: string;

  @ApiPropertyOptional({ type: [String], example: ['tasks:write', 'tasks:move', 'docs:write'] })
  @IsOptional()
  @IsArray()
  scopes?: string[];

  @ApiPropertyOptional({ example: '2027-01-01T00:00:00.000Z' })
  @IsOptional()
  @IsDateString()
  expiresAt?: string;
}
