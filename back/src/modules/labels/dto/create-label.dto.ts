import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { IsOptional, IsString, MaxLength } from 'class-validator';

export class CreateLabelDto {
  @ApiProperty({ example: 'Bug' })
  @IsString()
  @MaxLength(60)
  name: string;

  @ApiPropertyOptional({ example: '#FF0000', description: 'Cor opcional da etiqueta (ex.: hex).' })
  @IsOptional()
  @IsString()
  @MaxLength(30)
  color?: string;
}
