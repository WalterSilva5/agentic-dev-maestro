// Contexto multi-tenant resolvido por requisição (via API key ou JWT + X-Company-Id).
export interface ICompanyContext {
  companyId: number;
  userId: number;
  membershipId: number;
  role: string; // MembershipRole
  viaApiKeyId: number | null; // preenchido quando a ação veio de um agente
  scopes?: string[] | null;
}
