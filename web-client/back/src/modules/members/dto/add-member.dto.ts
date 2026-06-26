import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { IsEmail, IsEnum, IsOptional } from 'class-validator';
import { MembershipRole } from '@prisma/client';

export class AddMemberDto {
  @ApiProperty({ description: 'E-mail do usuário já cadastrado a ser adicionado.' })
  @IsEmail()
  email: string;

  @ApiPropertyOptional({ enum: MembershipRole, default: MembershipRole.DEV })
  @IsOptional()
  @IsEnum(MembershipRole)
  role?: MembershipRole;
}
