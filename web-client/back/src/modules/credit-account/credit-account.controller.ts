import { Controller, Post, Body, Get, Param, ParseIntPipe } from '@nestjs/common';
import { ApiBearerAuth, ApiOkResponse, ApiTags, ApiOperation } from '@nestjs/swagger';
import { AuthenticatedUser } from 'src/decorators/authenticated-user.decorator';
import { Roles } from 'src/decorators/role.decorator';
import { Role } from 'src/enums/role.enum';

import { CreditAccountService } from './credit-account.service';
import { UpdateBalanceDTO } from './dto/update-balance.dto';
import { CreditAccountDto } from './models/credit-account.dto';

@ApiTags('credits')
@ApiBearerAuth()
@Controller('credits')
export class CreditAccountController {
  constructor(private service: CreditAccountService) {}

  @Get('balance')
  @ApiOkResponse({ type: CreditAccountDto })
  async getBalance(
    @AuthenticatedUser() user: { id: number }
  ): Promise<CreditAccountDto> {
    await this.service.ensureDailyCredits(user.id);
    return this.service.getOrCreateAccount(user.id);
  }

  @Post('add')
  @ApiBearerAuth()
  @ApiOkResponse({ type: CreditAccountDto })
  async add(
    @AuthenticatedUser() user: { id: number },
    @Body() dto: UpdateBalanceDTO
  ): Promise<CreditAccountDto> {
    console.log(
      'Add credit request received for user:',
      dto.userId,
      'Amount:',
      dto.amount
    );
    return this.service.addCredit({ userId: dto.userId, amount: dto.amount });
  }

  @Post('subtract')
  @ApiBearerAuth()
  @ApiOkResponse({ type: CreditAccountDto })
  async subtract(
    @AuthenticatedUser() user: { id: number },
    @Body() dto: UpdateBalanceDTO
  ): Promise<CreditAccountDto> {
    return this.service.subtractCredit(dto.userId, dto.amount);
  }

  @Get('admin/user/:userId')
  @Roles(Role.ADMIN)
  @ApiOperation({ summary: 'Get user credit balance (Admin)' })
  @ApiOkResponse({ type: CreditAccountDto })
  async getUserBalance(
    @Param('userId', ParseIntPipe) userId: number
  ): Promise<CreditAccountDto> {
    return this.service.getOrCreateAccount(userId);
  }

  @Post('admin/add')
  @Roles(Role.ADMIN)
  @ApiOperation({ summary: 'Add credits to user account (Admin)' })
  @ApiOkResponse({ type: CreditAccountDto })
  async adminAddCredits(
    @Body() dto: UpdateBalanceDTO
  ): Promise<CreditAccountDto> {
    return this.service.addCredit(dto);
  }

  @Post('admin/subtract')
  @Roles(Role.ADMIN)
  @ApiOperation({ summary: 'Subtract credits from user account (Admin)' })
  @ApiOkResponse({ type: CreditAccountDto })
  async adminSubtractCredits(
    @Body() dto: UpdateBalanceDTO
  ): Promise<CreditAccountDto> {
    return this.service.subtractCredit(dto.userId, dto.amount);
  }
}
