import { Injectable } from '@nestjs/common';
import { PrismaService } from 'src/database/prisma/prisma.service';

// Garante que uma operação de criação rode uma única vez por (empresa, chave).
@Injectable()
export class IdempotencyService {
  constructor(private prisma: PrismaService) {}

  async run<T>(companyId: number, key: string | undefined, fn: () => Promise<T>): Promise<T> {
    if (!key) return fn();

    const existing = await this.prisma.idempotencyKey.findUnique({
      where: { companyId_key: { companyId, key } }
    });
    if (existing) return existing.response as T;

    const result = await fn();
    // normaliza para JSON puro (sem Date/instâncias) antes de persistir no Json
    const plain = JSON.parse(JSON.stringify(result));
    await this.prisma.idempotencyKey
      .create({ data: { companyId, key, response: plain } })
      .catch(() => undefined); // corrida: outra req gravou primeiro — tudo bem
    return result;
  }
}
