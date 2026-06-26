import { ApiProperty } from '@nestjs/swagger';

export class LoginDto {
  @ApiProperty({ default: 'admin@admin.com' })
  email: string;

  @ApiProperty({ default: 'Admin@123' })
  password: string;
}
