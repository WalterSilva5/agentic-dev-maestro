import { ApiProperty, ApiResponseProperty } from '@nestjs/swagger';
import { Role } from '@prisma/client';
import { IsDateString, IsEmail, IsEnum, IsNotEmpty, IsOptional, IsString } from 'class-validator';

export class UserDto {
  @ApiResponseProperty()
  id?: number;

  @ApiProperty()
  @IsString({ message: 'Uma string era esperada' })
  @IsNotEmpty({ message: 'Este item é obrigatório' })
  firstName: string;

  @ApiProperty()
  @IsString({ message: 'Uma string era esperada' })
  @IsNotEmpty({ message: 'Este item é obrigatório' })
  lastName: string;

  @ApiProperty({ required: false })
  @IsOptional()
  @IsString({ message: 'Uma string era esperada' })
  username?: string;

  @ApiProperty()
  @IsString({ message: 'Uma string era esperada' })
  @IsNotEmpty({ message: 'Este item é obrigatório' })
  @IsEmail({}, { message: 'Email inválido' })
  email: string;

  @ApiProperty({ required: false })
  @IsOptional()
  @IsEnum(Role, { message: 'Valor inválido' })
  role?: Role;

  @ApiProperty({ required: false })
  @IsOptional()
  @IsString({ message: 'Uma string era esperada' })
  gender?: string;

  @ApiProperty({ required: false })
  @IsOptional()
  @IsDateString({}, { message: 'Data inválida' })
  birthDate?: string;

  @ApiResponseProperty()
  createdAt?: string;

  @ApiResponseProperty()
  updatedAt?: string;

  @ApiResponseProperty()
  deletedAt?: string;
}
