import { ApiProperty } from '@nestjs/swagger';
import { TransactionType } from '@prisma/client';

export class CreditTransaction {
  @ApiProperty({
    description: 'Transaction ID',
    example: 1
  })
  id: number;

  @ApiProperty({
    description: 'Account ID',
    example: 1
  })
  accountId: number;

  @ApiProperty({
    description: 'Transaction type',
    enum: TransactionType,
    example: TransactionType.PURCHASE
  })
  type: TransactionType;

  @ApiProperty({
    description: 'Transaction amount (positive for purchase, negative for usage)',
    example: 100.5
  })
  amount: number;

  @ApiProperty({
    description: 'Transaction description',
    example: 'Purchase of credits',
    nullable: true
  })
  description?: string;

  @ApiProperty({
    description: 'Creation date',
    example: '2025-09-14T12:00:00.000Z'
  })
  createdAt: Date;

  @ApiProperty({
    description: 'Last update date',
    example: '2025-09-14T12:00:00.000Z',
    nullable: true
  })
  updatedAt?: Date;

  @ApiProperty({
    description: 'Deletion date',
    example: '2025-09-14T12:00:00.000Z',
    nullable: true
  })
  deletedAt?: Date;

  @ApiProperty({
    description: 'Credit account information',
    type: () => Object
  })
  account: {
    id: number;
    userId: number;
    balance: number;
    user: {
      id: number;
      firstName: string;
      lastName: string;
      email: string;
    };
  };
}
