import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { TenantService } from '../services/tenant.service';
import { WorkspaceService } from '../services/workspace.service';

// Exige um workspace ativo. Se não houver, tenta carregar (deep-link/refresh) e,
// persistindo vazio, manda para a seleção de workspaces. Deve rodar após o AuthGuard.
export const workspaceGuard: CanActivateFn = async () => {
  const tenant = inject(TenantService);
  const workspaces = inject(WorkspaceService);
  const router = inject(Router);

  if (tenant.companyId != null) return true;

  try {
    await workspaces.refresh();
  } catch {
    /* sem rede/sessão: cai no redirect abaixo */
  }

  if (tenant.companyId != null) return true;
  return router.createUrlTree(['/companies']);
};
