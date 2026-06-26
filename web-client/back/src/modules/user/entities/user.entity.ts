import { ApiResponseProperty } from '@nestjs/swagger';
import { Exclude } from 'class-transformer';
import { CreditAccountDto } from 'src/modules/credit-account/models/credit-account.dto';
import { Role } from '@prisma/client';

export class User {
  @ApiResponseProperty()
  id: number;

  @ApiResponseProperty()
  firstName: string;

  @ApiResponseProperty()
  lastName: string;

  @ApiResponseProperty()
  username?: string;

  @ApiResponseProperty()
  email: string;

  @ApiResponseProperty()
  role: Role;

  @ApiResponseProperty()
  gender?: string;

  @ApiResponseProperty()
  birthDate?: Date;

  @Exclude()
  sessionToken?: string;

  @Exclude()
  password?: string;

  @ApiResponseProperty()
  createdAt?: Date;

  @ApiResponseProperty()
  updatedAt?: Date;

  @ApiResponseProperty()
  deletedAt?: Date;

  @ApiResponseProperty({ type: () => CreditAccountDto })
  creditAccount?: CreditAccountDto;
}
