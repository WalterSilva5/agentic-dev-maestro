import { ApiProperty } from '@nestjs/swagger';
import { IsEmail, IsNotEmpty, IsString } from 'class-validator';

export class SimpleRegisterDto {
  @ApiProperty({ example: 'João' })
  @IsString({ message: 'Uma string era esperada' })
  @IsNotEmpty({ message: 'Este item é obrigatório' })
  firstName: string;

  @ApiProperty({ example: 'Silva' })
  @IsString({ message: 'Uma string era esperada' })
  @IsNotEmpty({ message: 'Este item é obrigatório' })
  lastName: string;

  @ApiProperty({ example: 'joao@email.com' })
  @IsEmail({}, { message: 'Email inválido' })
  @IsNotEmpty({ message: 'Este item é obrigatório' })
  email: string;

  @ApiProperty({ example: 'senha123' })
  @IsString({ message: 'Uma string era esperada' })
  @IsNotEmpty({ message: 'Este item é obrigatório' })
  password: string;
}
