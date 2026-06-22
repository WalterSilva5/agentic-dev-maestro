import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { IsOptional, IsString, MaxLength } from 'class-validator';

export class CreateCompanyDto {
  @ApiProperty({ example: 'Minha Empresa' })
  @IsString()
  @MaxLength(120)
  name: string;

  @ApiPropertyOptional({ example: 'minha-empresa', description: 'Opcional; derivado do nome se ausente.' })
  @IsOptional()
  @IsString()
  @MaxLength(120)
  slug?: string;
}
