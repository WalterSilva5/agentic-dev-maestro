import { Injectable } from '@nestjs/common';
import type { CreditAccount } from '@prisma/client';
import { PrismaService } from 'src/database/prisma/prisma.service';
import type { Paginated } from 'src/interfaces/IPaginated';

import type { CreditTransactionFilterDTO } from './dto/credit-transaction-filter.dto';
import type { CreditTransaction } from './entities/credit-transaction.entity';

@Injectable()
export class CreditTransactionService {
  constructor(private prisma: PrismaService) {}

  private async findUserAccount(userId: number): Promise<CreditAccount | null> {
    // Busca a conta ativa do usuário
    return this.prisma.creditAccount.findFirst({
      where: {
        userId,
        deletedAt: null
      },
      orderBy: {
        createdAt: 'desc'
      }
    });
  }

  private buildEmptyResponse(page: number, limit: number): Paginated<CreditTransaction> {
    return {
      data: [],
      meta: {
        total: 0,
        lastPage: 0,
        currentPage: page,
        perPage: limit,
        prev: null,
        next: null
      }
    };
  }

  async findByUserId(
    filter: CreditTransactionFilterDTO
  ): Promise<Paginated<CreditTransaction>> {
    const { page, limit, type, startDate, endDate } = filter;
    const skip = (page - 1) * limit;

    console.log(`Buscando conta para o usuário com ID: ${filter.userId}`);

    // Primeiro busca a conta do usuário
    const userAccount = await this.findUserAccount(filter.userId);

    console.log(`Conta encontrwa: ${JSON.stringify(userAccount)}`);
    //espere 20 segundos antes  de continuar
    if (!userAccount) {
      console.log(`Nenhuma conta encontrada para o usuário com ID: ${filter.userId}`);
      return this.buildEmptyResponse(page, limit);
    }

    // Usa o ID da conta para buscar as transações
    const whereClause = this.buildWhereClause(userAccount.id, type, startDate, endDate);

    console.log(`Filtro aplicado: ${JSON.stringify(whereClause)}`);

    const [total, transactions] = await Promise.all([
      this.prisma.creditTransaction.count({ where: whereClause }),
      this.getTransactionsWithAccount(whereClause, skip, limit)
    ]);
    console.log(`Total de transações encontradas: ${total}`);

    const totalPages = Math.ceil(total / limit);

    return {
      data: transactions as CreditTransaction[],
      meta: {
        total,
        lastPage: totalPages,
        currentPage: page,
        perPage: limit,
        prev: page > 1 ? page - 1 : null,
        next: page < totalPages ? page + 1 : null
      }
    };
  }

  private buildWhereClause(
    accountId: number,
    type?: string,
    startDate?: string,
    endDate?: string
  ) {
    // Filtro base usando o ID da conta diretamente
    const where = {
      accountId,
      deletedAt: null
    } as const;

    if (type) {
      where['type'] = type;
    }

    if (startDate || endDate) {
      where['createdAt'] = {};
      if (startDate) where['createdAt']['gte'] = new Date(startDate);
      if (endDate) where['createdAt']['lte'] = new Date(endDate);
    }

    return where;
  }

  private async getTransactionsWithAccount(
    where: Record<string, any>,
    skip: number,
    take: number
  ) {
    return this.prisma.creditTransaction.findMany({
      where,
      include: {
        account: {
          include: {
            user: {
              select: {
                id: true,
                firstName: true,
                lastName: true,
                email: true
              }
            }
          }
        }
      },
      orderBy: {
        createdAt: 'desc'
      },
      skip,
      take
    });
  }

  async findById(id: number): Promise<CreditTransaction | null> {
    return this.prisma.creditTransaction.findUnique({
      where: { id },
      include: {
        account: {
          include: {
            user: {
              select: {
                id: true,
                firstName: true,
                lastName: true,
                email: true
              }
            }
          }
        }
      }
    }) as Promise<CreditTransaction | null>;
  }
}
