import { ApiProperty } from '@nestjs/swagger';
import { Exclude } from 'class-transformer';
import { IsNotEmpty, IsString } from 'class-validator';
import { UserDto } from 'src/modules/user/models/user.dto';

export class RegisterDto extends UserDto {
  @ApiProperty()
  @IsString({ message: 'Uma string era esperada' })
  @IsNotEmpty({ message: 'Este item é obrigatório' })
  @Exclude({ toPlainOnly: true })
  password: string;
}
