import type { ExecutionContext } from '@nestjs/common';
import { createParamDecorator } from '@nestjs/common';
import type { IAuthRequest } from 'src/interfaces/IAuthRequest';
import type { User } from 'src/modules/user/entities/user.entity';

export const AuthenticatedUser = createParamDecorator(
  (data: unknown, context: ExecutionContext): User => {
    const request = context.switchToHttp().getRequest<IAuthRequest>();
    return request.user;
  }
);
