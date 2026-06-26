import { Injectable, BadRequestException, Logger } from '@nestjs/common';
import { TransactionType } from '@prisma/client';
import type { CreditAccount } from '@prisma/client';
import { PrismaService } from 'src/database/prisma/prisma.service';

import type { UpdateBalanceDTO } from './dto/update-balance.dto';

@Injectable()
export class CreditAccountService {
  private readonly logger = new Logger(CreditAccountService.name);

  constructor(private prisma: PrismaService) {}
  //TODO passar para repository

  async ensureDailyCredits(userId: number): Promise<void> {
    const now = new Date();
    const startOfDay = this.getStartOfDay(now);
    let account = await this.getOrCreateAccount(userId);
    const last = (account as any).lastDailyCredit as Date | null;

    if (this.shouldGrantDailyCredits(last, startOfDay, account.balance)) {
      await this.grantDailyCredits(account, now, userId);
    }
  }

  private getStartOfDay(date: Date): Date {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate());
  }

  private shouldGrantDailyCredits(
    last: Date | null,
    startOfDay: Date,
    balance: number
  ): boolean {
    return (last == null || last < startOfDay) && balance < 15;
  }

  private async grantDailyCredits(
    account: CreditAccount,
    now: Date,
    userId: number
  ): Promise<void> {
    const toAdd = 15 - account.balance;
    await this.prisma.creditAccount.update({
      where: { id: account.id },
      data: { balance: { increment: toAdd }, lastDailyCredit: now }
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);
    await this.prisma.creditTransaction.create({
      data: { accountId: account.id, type: TransactionType.PURCHASE, amount: toAdd }
    });
    this.logger.log(`Granted daily credits: ${toAdd} for user ${userId}`);
  }

  async getOrCreateAccount(userId: number): Promise<CreditAccount> {
    this.logger.debug(`Fetching credit account for user ${userId}`);
    let account: CreditAccount | null = await this.prisma.creditAccount.findUnique({
      where: { userId }
    });
    if (!account) {
      this.logger.log(`Creating new credit account for user ${userId}`);
      account = await this.prisma.creditAccount.create({ data: { userId } });
    }
    return account;
  }

  async addCredit(dto: UpdateBalanceDTO): Promise<CreditAccount> {
    const { userId, amount } = dto;
    this.logger.debug(`Adding ${amount} credits to user ${userId}`);

    if (amount <= 0) {
      this.logger.warn(`Invalid amount attempted: ${amount}`);
      throw new BadRequestException('Amount must be positive');
    }

    const account: CreditAccount = await this.getOrCreateAccount(userId);
    const updated: CreditAccount = await this.prisma.creditAccount.update({
      where: { id: account.id },
      data: { balance: { increment: amount } }
    });
    console.log('Account after adding credit:', updated);

    await this.prisma.creditTransaction.create({
      data: {
        accountId: account.id,
        type: TransactionType.PURCHASE,
        amount
      }
    });

    this.logger.log(`Successfully added ${amount} credits to account ${account.id}`);
    return updated;
  }

  async subtractCredit(userId: number, amount: number): Promise<CreditAccount> {
    this.logger.debug(`Attempting to subtract ${amount} credits from user ${userId}`);

    if (amount <= 0) {
      this.logger.warn(`Invalid deduction amount attempted: ${amount}`);
      throw new BadRequestException('Amount must be positive');
    }

    const account: CreditAccount = await this.getOrCreateAccount(userId);

    // Se o valor a ser subtraído for maior que o saldo, usa todo o saldo disponível
    const deductionAmount = Math.min(amount, account.balance);

    const updated: CreditAccount = await this.prisma.creditAccount.update({
      where: { id: account.id },
      data: { balance: { decrement: deductionAmount } }
    });

    await this.prisma.creditTransaction.create({
      data: {
        accountId: account.id,
        type: TransactionType.USAGE,
        amount: deductionAmount
      }
    });

    if (deductionAmount < amount) {
      this.logger.warn(
        `Partial deduction for user ${userId}: requested ${amount}, deducted ${deductionAmount} (account zeroed)`
      );
    }

    this.logger.log(`Successfully deducted ${amount} credits from account ${account.id}`);
    return updated;
  }
}
