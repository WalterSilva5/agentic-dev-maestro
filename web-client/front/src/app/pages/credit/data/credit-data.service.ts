import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import Swal from 'sweetalert2';
import { CreditApiService } from '../api/credit-api.service';

type CreditResponse = Record<string, unknown>;

@Injectable({ providedIn: 'root' })
export class CreditDataService {
  private api = inject(CreditApiService);

  async addCredit(userId: number, amount: number): Promise<CreditResponse> {
    const payload: Record<string, unknown> = { userId, amount };
    console.log('CreditDataService addCredit payload: ', payload);
    try {
      const res = await firstValueFrom(this.api.addCredit(payload));
      Swal.fire('Success', 'Credits added successfully', 'success');
      return res as CreditResponse;
    } catch (err: unknown) {
      console.error('error adding credits', err);
  const msg = extractErrorMessage(err) || 'Failed to add credits';
      Swal.fire('Error', msg, 'error');
      throw err;
    }
  }

  async subtractCredit(userId: number, amount: number): Promise<CreditResponse> {
    const payload: Record<string, unknown> = { userId, amount };
    try {
      const res = await firstValueFrom(this.api.subtractCredit(payload));
      Swal.fire('Success', 'Credits subtracted successfully', 'success');
      return res as CreditResponse;
    } catch (err: unknown) {
      console.error('error subtracting credits', err);
      const msg = extractErrorMessage(err) || 'Failed to subtract credits';
      Swal.fire('Error', msg, 'error');
      throw err;
    }
  }
}

function extractErrorMessage(err: unknown): string | undefined {
  if (!err) return undefined;
  // HttpErrorResponse typical shape: { error: { message: string } }
  try {
    const e = err as { error?: { message?: string }; message?: string };
    return e?.error?.message ?? e?.message;
  } catch {
    return undefined;
  }
}
