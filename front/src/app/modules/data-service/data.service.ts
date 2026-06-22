import { Injectable, Injector } from '@angular/core';
import { HttpClient, HttpHeaders, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { ConfigService } from '../../services/config.service';
import { selectAuth } from '../../state/auth/auth.selectors';
import { Store } from '@ngrx/store';
import { Router } from '@angular/router';

@Injectable({
  providedIn: 'root'
})
export class DataService {
  public apiUrl: string;
  REQUEST_TIMEOUT = 3000000;
  token = '';

  protected http: HttpClient;
  protected store: Store<any>;
  protected router: Router;
  protected configService: ConfigService;

  constructor(private injector: Injector) {
    this.http = this.injector.get(HttpClient);
    this.store = this.injector.get(Store);
    this.router = this.injector.get(Router);
    this.configService = this.injector.get(ConfigService);
    
    this.apiUrl = this.configService.apiUrl;

    this.store.select(selectAuth).subscribe((auth) => {
      this.token = auth?.accessToken || '';
    });
  }

  protected getHeaders(authenticated = true): HttpHeaders {
    let headers = new HttpHeaders();
    if (authenticated && this.token) {
      headers = headers.set('Authorization', `Bearer ${this.token}`);
    }
    return headers;
  }

  /**
   * Constrói uma string de consulta (query string) a partir de um objeto de filtros.
   * Suporta os filtros definidos na classe DefaultFilter.
   */
  protected buildQueryString(filters: Record<string, any>): string {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        if (typeof value === 'object' && !Array.isArray(value)) {
          params.append(key, JSON.stringify(value));
        } else {
          params.append(key, value.toString());
        }
      }
    });
    return params.toString();
  }

  public getManyData<T>(
    endpoint?: string,
    filters?: Record<string, any>,
    authenticated = true
  ): Observable<T> {
    const queryString = filters ? `?${this.buildQueryString(filters)}` : '';
    const url = this.buildUrl(endpoint) + queryString;
    const headers = this.getHeaders(authenticated);
    console.log('GET URL:', url);
    console.log('\n\nHEADERS:', headers);
    console.log('FILTERS:', filters);
    return this.http
      .get<T>(url, { headers })
      .pipe(
        catchError((error) => this.handleError<T>(error))
      );
  }

  public getOneData<T>(
    id: string,
    endpoint?: string,
    authenticated = true
  ): Observable<T> {
    const url = this.buildUrl(endpoint, id);
    const headers = this.getHeaders(authenticated);
    return this.http
      .get<T>(url, { headers })
      .pipe(
        catchError((error) => this.handleError<T>(error))
      );
  }

  public postData<T>(
    data: T,
    endpoint?: string,
    authenticated = true
  ): Observable<T> {
    const url = this.buildUrl(endpoint);
    const headers = this.getHeaders(authenticated);
    return this.http
      .post<T>(url, data, { headers })
      .pipe(
        catchError((error) => this.handleError<T>(error))
      );
  }

  public updateData<T>(
    data: T,
    id: string,
    endpoint?: string,
    authenticated = true
  ): Observable<T> {
    const url = this.buildUrl(endpoint, id);
    const headers = this.getHeaders(authenticated);
    return this.http
      .put<T>(url, data, { headers })
      .pipe(
        catchError((error) => this.handleError<T>(error))
      );
  }

  public deleteData(
    id: string,
    endpoint?: string,
    authenticated = true
  ): Observable<object | undefined> {
    const url = this.buildUrl(endpoint, id);
    const headers = this.getHeaders(authenticated);
    return this.http
      .delete<object | undefined>(url, { headers })
      .pipe(
        catchError((error) => this.handleError<object | undefined>(error))
      );
  }

  /**
   * Método para tentar fazer refresh do token. Deve ser sobrescrito nos serviços filhos se necessário.
   */
  protected refreshToken(): Observable<boolean> {
    // Por padrão, retorna erro. Serviços filhos podem sobrescrever.
    return throwError('Refresh token não implementado.');
  }

  /**
   * Tratamento centralizado de erros.
   */
  public handleError<T>(error: unknown): Observable<T> {
    if (error instanceof HttpErrorResponse) {
      // 401 is handled by auth interceptor (refresh token flow)
      // Do NOT redirect to login here - let the interceptor handle it
      if (error.status !== 401) {
        this.logError('HTTP error received', error);
      }
      return throwError(() => error);
    }
    this.logError('Non-HTTP error received', error);
    return throwError(() => error);
  }

  /**
   * Trata erros de timeout e rede.
   */
  public handleTimeoutError(error: unknown): Observable<Record<string, unknown>> {
    if (this.isNetworkError(error)) {
      return of({ success: true, message: 'Upload concluído com sucesso!' });
    }
    if (this.isTimeoutError(error)) {
      console.warn('Timeout or unknown error ignored');
      return of({ success: true, message: 'Request completed successfully' });
    }
    this.logError('Erro desconhecido de timeout/rede', error);
    return throwError(() => error);
  }

  /**
   * Monta a URL base para as requisições.
   */
  private buildUrl(endpoint?: string, id?: string): string {
    let url = `${this.apiUrl}`;
    if (endpoint) url += `/${endpoint}`;
    if (id) url += `/${id}`;
    return url;
  }

  /**
   * Monta a mensagem de erro amigável.
   */
  private buildErrorMessage(error: HttpErrorResponse): string {
    if (error.error && error.error.message) {
      return `Erro: ${error.error.message}`;
    }
    return `Código do erro: ${error.status}\nMensagem: ${error.message}`;
  }

  /**
   * Verifica se o erro é de rede.
   */
  private isNetworkError(error: unknown): boolean {
    return error != null && typeof error === 'object' && 'message' in error && error.message === 'Network Error';
  }

  /**
   * Verifica se o erro é timeout (504 ou 0).
   */
  private isTimeoutError(error: unknown): boolean {
    return (
      error instanceof HttpErrorResponse && (error.status === 504 || error.status === 0)
    );
  }

  /**
   * Loga o erro no console.
   */
  private logError(message: string, error?: unknown): void {
    console.error(message);
    if (error) {
      console.error(error);
    }
  }
}
