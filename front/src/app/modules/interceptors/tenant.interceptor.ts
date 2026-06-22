import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';

import { TenantService } from '../../services/tenant.service';

// Injeta X-Company-Id (empresa ativa) em toda requisição autenticada por JWT,
// para os endpoints multi-tenant do backend (projetos, tarefas, docs, etc.).
export const tenantInterceptor: HttpInterceptorFn = (req, next) => {
  const tenant = inject(TenantService);
  const companyId = tenant.companyId;
  if (companyId && !req.headers.has('X-Company-Id')) {
    return next(req.clone({ setHeaders: { 'X-Company-Id': String(companyId) } }));
  }
  return next(req);
};
