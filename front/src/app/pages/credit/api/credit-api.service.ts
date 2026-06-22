import { Injectable, Injector } from '@angular/core';
import { DataService } from '../../../modules/data-service/data.service';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class CreditApiService extends DataService {
  endpoint = 'credits';

  constructor(injector: Injector) {
    super(injector);
  }

  addCredit(payload: Record<string, unknown>): Observable<Record<string, unknown>> {
    return this.postData<Record<string, unknown>>(payload, `${this.endpoint}/add`);
  }

  subtractCredit(payload: Record<string, unknown>): Observable<Record<string, unknown>> {
    return this.postData<Record<string, unknown>>(payload, `${this.endpoint}/subtract`);
  }
}
