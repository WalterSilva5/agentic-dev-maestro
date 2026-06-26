import { SetMetadata } from '@nestjs/common';

// Exige um dos papéis de membership (OWNER/MANAGER/TECH_LEAD/DEV/VIEWER)
// no contexto de empresa. Verificado pelo ApiAccessGuard.
export const COMPANY_ROLES_KEY = 'company_roles';
export const RequireRole = (...roles: string[]) => SetMetadata(COMPANY_ROLES_KEY, roles);
