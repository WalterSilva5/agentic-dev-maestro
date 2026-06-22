import type { Request } from 'express';
import type { User } from 'src/modules/user/entities/user.entity';

export interface IAuthRequest extends Request {
  user: User;
}
