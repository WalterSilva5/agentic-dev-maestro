import { Injectable, Injector } from '@angular/core';
import { DataService } from '../../../modules/data-service/data.service';
import { HttpClient } from '@angular/common/http';
import { catchError, firstValueFrom, Observable, tap, throwError, timeout } from 'rxjs';
import { PaginatedData } from '../../../models/paginated-data.type';
import { HttpErrorResponse } from '@angular/common/http';
import { of } from 'rxjs';
import { AuthDto } from '../dto/auth-data.dto';
import { Store } from '@ngrx/store';

@Injectable({
  providedIn: 'root'
})
export class AuthApiService extends DataService {
  constructor(injector: Injector) {
    super(injector);
  }

  login(authData: AuthDto): Observable<any> {
    return this.http.post(`${this.apiUrl}/auth/login`, authData).pipe(
      tap((response: any) => {
        return response;
      }),
      catchError((error: HttpErrorResponse) => {
        console.error('error', error);
        return of(error);
      })
    );
  }

  getMe(accessToken: string): Observable<any> {
    const headers = { Authorization: `Bearer ${accessToken}` };
    return this.http.get(`${this.apiUrl}/user/me`, { headers }).pipe(
      tap((response: any) => {
        return response;
      }),
      catchError((error: HttpErrorResponse) => {
        console.error('error', error);
        return of(error);
      })
    );
  }

  exchangeCode(code: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/auth/google/callback`, { code }).pipe(
      tap((response: any) => {
        return response;
      }),
      catchError((error: HttpErrorResponse) => {
        console.error('error', error);
        return of(error);
      })
    );
  }

  refresh(refreshToken: string): Observable<any> {
    const headers = { Authorization: `Bearer ${refreshToken}` };
    return this.http.post(`${this.apiUrl}/auth/refresh`, {}, { headers }).pipe(
      tap((response: any) => {
        return response;
      }),
      catchError((error: HttpErrorResponse) => {
        console.error('Erro ao fazer refresh do token:', error);
        return throwError(() => error);
      })
    );
  }

  forgotPassword(email: string): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${this.apiUrl}/auth/forgot-password`, { email }).pipe(
      timeout(10000),
      catchError((error: HttpErrorResponse) => {
        console.error('Erro ao solicitar recuperação de senha:', error);
        return throwError(() => error);
      })
    );
  }

  validateResetToken(token: string): Observable<{ valid: boolean; email?: string }> {
    return this.http.get<{ valid: boolean; email?: string }>(`${this.apiUrl}/auth/validate-reset-token/${token}`).pipe(
      timeout(10000),
      catchError((error: HttpErrorResponse) => {
        console.error('Erro ao validar token:', error);
        return throwError(() => error);
      })
    );
  }

  resetPassword(token: string, newPassword: string): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${this.apiUrl}/auth/reset-password`, { token, newPassword }).pipe(
      timeout(10000),
      catchError((error: HttpErrorResponse) => {
        console.error('Erro ao resetar senha:', error);
        return throwError(() => error);
      })
    );
  }

  changePassword(currentPassword: string, newPassword: string): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${this.apiUrl}/auth/change-password`, { currentPassword, newPassword }).pipe(
      timeout(10000),
      catchError((error: HttpErrorResponse) => {
        console.error('Erro ao alterar senha:', error);
        return throwError(() => error);
      })
    );
  }
}
