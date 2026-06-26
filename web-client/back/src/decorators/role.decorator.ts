import { SetMetadata } from '@nestjs/common';
import type { Role } from 'src/enums/role.enum';

export const ROLES_KEY = 'role';
export const Roles = (...role: Role[]) => SetMetadata(ROLES_KEY, role);
