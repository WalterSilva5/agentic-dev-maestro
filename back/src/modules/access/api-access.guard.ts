import type { CanActivate, ExecutionContext } from '@nestjs/common';
import { Injectable, UnauthorizedException } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { PrismaService } from 'src/database/prisma/prisma.service';
import type { ICompanyContext } from 'src/interfaces/ICompanyContext';
import { ApiKeyService } from 'src/modules/api-key/api-key.service';

interface RequestWithContext {
  headers: Record<string, string | string[] | undefined>;
  user?: unknown;
  companyContext?: ICompanyContext;
}

// Aceita autenticação por API key (agente) OU JWT + X-Company-Id (humano)
// e preenche req.user + req.companyContext. Ver docs/04-rbac-e-multitenant.md.
@Injectable()
export class ApiAccessGuard implements CanActivate {
  constructor(
    private readonly apiKeyService: ApiKeyService,
    private readonly jwt: JwtService,
    private readonly prisma: PrismaService
  ) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const req = context.switchToHttp().getRequest<RequestWithContext>();

    const apiKeyHeader = this.header(req, 'x-api-key');
    if (apiKeyHeader) {
      const result = await this.apiKeyService.validate(apiKeyHeader);
      if (!result) throw new UnauthorizedException('API key inválida, expirada ou revogada');
      const { apiKey, membership } = result;
      req.user = membership.user;
      req.companyContext = {
        companyId: apiKey.companyId,
        userId: membership.userId,
        membershipId: membership.id,
        role: membership.role,
        viaApiKeyId: apiKey.id,
        scopes: (apiKey.scopes as string[] | null) ?? null
      };
      return true;
    }

    // Sem API key → exige Bearer token (humano)
    const auth = this.header(req, 'authorization') ?? '';
    const token = auth.startsWith('Bearer ') ? auth.slice(7) : null;
    if (!token) throw new UnauthorizedException('Forneça uma API key (x-api-key) ou um Bearer token');

    let payload: { id: number };
    try {
      payload = await this.jwt.verifyAsync(token, { secret: process.env.AT_SECRET });
    } catch {
      throw new UnauthorizedException('Token inválido ou expirado');
    }
    req.user = payload;

    const companyIdHeader = this.header(req, 'x-company-id');
    if (companyIdHeader) {
      const companyId = Number(companyIdHeader);
      const membership = await this.prisma.membership.findUnique({
        where: { userId_companyId: { userId: payload.id, companyId } }
      });
      if (!membership) throw new UnauthorizedException('Usuário não pertence a esta empresa');
      req.companyContext = {
        companyId,
        userId: payload.id,
        membershipId: membership.id,
        role: membership.role,
        viaApiKeyId: null,
        scopes: null
      };
    }
    return true;
  }

  private header(req: RequestWithContext, name: string): string | undefined {
    const value = req.headers[name];
    return Array.isArray(value) ? value[0] : value;
  }
}
