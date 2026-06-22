import { ApiResponseProperty } from '@nestjs/swagger';
import { User } from 'src/modules/user/entities/user.entity';

export class JWTTokenDto {
  @ApiResponseProperty()
  accessToken: string;

  @ApiResponseProperty()
  refreshToken: string;

  @ApiResponseProperty()
  user: User;
}
