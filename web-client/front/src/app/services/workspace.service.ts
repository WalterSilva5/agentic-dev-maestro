import { Injectable } from '@angular/core';

import { MaestroApiService } from './maestro-api.service';
import { TenantService, ActiveCompany } from './tenant.service';

// Carrega a lista de workspaces do usuário e mantém o ativo coerente.
// Mantido separado do TenantService para evitar dependência circular com o HttpClient.
@Injectable({ providedIn: 'root' })
export class WorkspaceService {
  constructor(
    private api: MaestroApiService,
    private tenant: TenantService
  ) {}

  // Busca os workspaces e garante um ativo (auto-seleção). Retorna a lista.
  async refresh(): Promise<ActiveCompany[]> {
    const companies = await this.api.listCompanies();
    const list: ActiveCompany[] = companies.map((c) => ({
      id: c.id,
      name: c.name,
      role: c.memberships?.[0]?.role || 'DEV'
    }));
    this.tenant.setWorkspaces(list);
    return list;
  }
}
