import { Injectable, Injector } from '@angular/core';
import { DataService } from '../../../modules/data-service/data.service';
import { Observable } from 'rxjs';
import { PaginatedData } from '../../../models/paginated-data.type';

export interface CreditTransaction {
  id: number;
  type: string;
  amount: number;
  description?: string;
  createdAt: string;
  user: {
    id: number;
    firstName: string;
    lastName: string;
    email: string;
  };
}

export interface CreditTransactionFilters {
  page?: number;
  limit?: number;
  type?: string;
  startDate?: string;
  endDate?: string;
  userId: number;
}

@Injectable({ providedIn: 'root' })
export class CreditTransactionApiService extends DataService {
  endpoint = 'credit-transactions';

  constructor(injector: Injector) {
    super(injector);
  }

  getUserTransactions(filters: CreditTransactionFilters): Observable<PaginatedData<CreditTransaction>> {
    return this.getManyData<PaginatedData<CreditTransaction>>(this.endpoint, filters);
  }

  getTransactionById(id: string): Observable<CreditTransaction> {
    return this.getOneData<CreditTransaction>(id, this.endpoint);
  }
}
