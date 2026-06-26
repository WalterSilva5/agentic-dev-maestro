import { ApiProperty } from '@nestjs/swagger';
import { IsString } from 'class-validator';

export class AddDependencyDto {
  @ApiProperty({
    example: 'DEMO-2',
    description: 'Código da tarefa que BLOQUEIA (precisa concluir antes desta).'
  })
  @IsString()
  blockerCode: string;
}
