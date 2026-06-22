import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { PaginatedData } from '../../../models/paginated-data.type';
import { CreditTransactionApiService, CreditTransaction, CreditTransactionFilters } from '../api/credit-transaction-api.service';

@Injectable({ providedIn: 'root' })
export class CreditTransactionDataService {
  private api = inject(CreditTransactionApiService);

  async getUserTransactions(filters: CreditTransactionFilters): Promise<PaginatedData<CreditTransaction>> {
    try {
      return await firstValueFrom(this.api.getUserTransactions(filters));
    } catch (err: unknown) {
      console.error('Error fetching credit transactions:', err);
      throw err;
    }
  }

  async getTransactionById(id: number): Promise<CreditTransaction> {
    try {
      return await firstValueFrom(this.api.getTransactionById(id.toString()));
    } catch (err: unknown) {
      console.error('Error fetching credit transaction by id:', err);
      throw err;
    }
  }
}
