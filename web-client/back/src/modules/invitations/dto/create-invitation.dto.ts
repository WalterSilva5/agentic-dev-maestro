import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { IsEmail, IsEnum, IsOptional } from 'class-validator';
import { MembershipRole } from '@prisma/client';

export class CreateInvitationDto {
  @ApiProperty({ description: 'E-mail do convidado (com ou sem conta no sistema).' })
  @IsEmail()
  email: string;

  @ApiPropertyOptional({ enum: MembershipRole, default: MembershipRole.DEV })
  @IsOptional()
  @IsEnum(MembershipRole)
  role?: MembershipRole;
}
