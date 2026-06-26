import { Controller, Get, Query, Param, ParseIntPipe } from '@nestjs/common';
import { ApiBearerAuth, ApiOkResponse, ApiTags } from '@nestjs/swagger';
import { ApiOkResponsePaginated } from 'src/interfaces/IPaginated';

import { CreditTransactionService } from './credit-transaction.service';
import { CreditTransactionFilterDTO } from './dto/credit-transaction-filter.dto';
import { CreditTransactionDto } from './models/credit-transaction.dto';

@ApiTags('credit-transactions')
@Controller('credit-transactions')
@ApiBearerAuth()
export class CreditTransactionController {
  constructor(private readonly service: CreditTransactionService) {}

  @Get()
  @ApiBearerAuth()
  @ApiOkResponsePaginated(CreditTransactionDto)
  async getUserTransactions(@Query() filter: CreditTransactionFilterDTO) {
    return this.service.findByUserId(filter);
  }

  @Get(':id')
  @ApiOkResponse({ type: CreditTransactionDto })
  async getTransactionById(@Param('id', ParseIntPipe) id: number) {
    return this.service.findById(id);
  }

  @Get('admin/all')
  @ApiBearerAuth()
  @ApiOkResponsePaginated(CreditTransactionDto)
  async getAllTransactions(@Query() _filter: CreditTransactionFilterDTO) {
    return {
      data: [],
      meta: {
        total: 0,
        lastPage: 0,
        currentPage: 1,
        perPage: 10,
        prev: null,
        next: null
      }
    };
  }
}
