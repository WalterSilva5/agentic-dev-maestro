import { createHash, randomBytes } from 'crypto';

import { Injectable, NotFoundException } from '@nestjs/common';
import { PrismaService } from 'src/database/prisma/prisma.service';

import type { CreateApiKeyDto } from './dto/create-api-key.dto';

export interface ApiKeyValidation {
  apiKey: {
    id: number;
    companyId: number;
    membershipId: number;
    scopes: unknown;
  };
  membership: {
    id: number;
    userId: number;
    companyId: number;
    role: string;
    user: unknown;
  };
}

@Injectable()
export class ApiKeyService {
  constructor(private prisma: PrismaService) {}

  static hash(raw: string): string {
    return createHash('sha256').update(raw).digest('hex');
  }

  // Valida o segredo recebido no header x-api-key.
  async validate(rawKey: string): Promise<ApiKeyValidation | null> {
    const hashedKey = ApiKeyService.hash(rawKey);
    const apiKey = await this.prisma.apiKey.findUnique({
      where: { hashedKey },
      include: { membership: { include: { user: true } } }
    });
    if (!apiKey || apiKey.revokedAt) return null;
    if (apiKey.expiresAt && apiKey.expiresAt.getTime() < Date.now()) return null;

    // marca o último uso sem bloquear a requisição
    this.prisma.apiKey
      .update({ where: { id: apiKey.id }, data: { lastUsedAt: new Date() } })
      .catch(() => undefined);

    return { apiKey, membership: apiKey.membership } as ApiKeyValidation;
  }

  // Cria a chave e retorna o segredo em texto plano UMA única vez.
  async create(companyId: number, membershipId: number, dto: CreateApiKeyDto) {
    const secret = `adm_${randomBytes(24).toString('hex')}`;
    const created = await this.prisma.apiKey.create({
      data: {
        label: dto.label,
        hashedKey: ApiKeyService.hash(secret),
        prefix: secret.slice(0, 12),
        scopes: dto.scopes ?? undefined,
        companyId,
        membershipId,
        expiresAt: dto.expiresAt ? new Date(dto.expiresAt) : null
      }
    });
    return {
      id: created.id,
      label: created.label,
      prefix: created.prefix,
      secret // exibido só aqui — não é recuperável depois
    };
  }

  list(companyId: number) {
    return this.prisma.apiKey.findMany({
      where: { companyId, revokedAt: null },
      select: {
        id: true,
        label: true,
        prefix: true,
        scopes: true,
        lastUsedAt: true,
        expiresAt: true,
        createdAt: true
      }
    });
  }

  async revoke(companyId: number, id: number) {
    const key = await this.prisma.apiKey.findFirst({ where: { id, companyId } });
    if (!key) throw new NotFoundException('API key não encontrada');
    await this.prisma.apiKey.update({ where: { id }, data: { revokedAt: new Date() } });
    return { revoked: true };
  }
}
