import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { IsArray, IsBoolean, IsOptional, IsString, IsUrl } from 'class-validator';

export class CreateWebhookDto {
  @ApiProperty({ description: 'URL de destino que receberá os eventos via POST' })
  @IsUrl()
  url: string;

  @ApiPropertyOptional({ description: 'Segredo usado para assinar o payload (HMAC-SHA256)' })
  @IsOptional()
  @IsString()
  secret?: string;

  @ApiPropertyOptional({
    description: 'Eventos a escutar; vazio/ausente = todos os eventos',
    type: [String]
  })
  @IsOptional()
  @IsArray()
  @IsString({ each: true })
  events?: string[];
}

export class UpdateWebhookDto {
  @ApiPropertyOptional({ description: 'Ativa/desativa o webhook' })
  @IsOptional()
  @IsBoolean()
  active?: boolean;

  @ApiPropertyOptional({ description: 'URL de destino que receberá os eventos via POST' })
  @IsOptional()
  @IsUrl()
  url?: string;

  @ApiPropertyOptional({
    description: 'Eventos a escutar; vazio/ausente = todos os eventos',
    type: [String]
  })
  @IsOptional()
  @IsArray()
  @IsString({ each: true })
  events?: string[];
}
