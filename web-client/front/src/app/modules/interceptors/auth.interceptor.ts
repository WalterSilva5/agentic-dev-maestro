import {
  HttpErrorResponse,
  HttpHandlerFn,
  HttpInterceptorFn,
  HttpRequest
} from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { Store } from '@ngrx/store';
import {
  BehaviorSubject,
  catchError,
  filter,
  first,
  switchMap,
  take,
  throwError,
  combineLatest
} from 'rxjs';
import { selectAuthToken, selectRefreshToken, selectUser } from '../../state/auth/auth.selectors';
import * as AuthActions from '../../state/auth/auth.actions';
import { AuthApiService } from '../../pages/auth/provider/auth-api.service';

// Controle de estado do refresh
let isRefreshing = false;
let refreshTokenSubject = new BehaviorSubject<string | null>(null);

function resetRefreshSubject() {
  refreshTokenSubject = new BehaviorSubject<string | null>(null);
}

export const authInterceptor: HttpInterceptorFn = (req: HttpRequest<unknown>, next: HttpHandlerFn) => {
  const store = inject(Store);
  const router = inject(Router);
  const authApiService = inject(AuthApiService);

  // Não interceptar requisições de refresh, login ou registro
  if (
    req.url.includes('auth/refresh') ||
    req.url.includes('auth/login') ||
    req.url.includes('auth/register') ||
    req.url.includes('auth/google')
  ) {
    return next(req);
  }

  return store.select(selectAuthToken).pipe(
    first(),
    switchMap(token => {
      // Adicionar token se existir
      const authReq = token ? addTokenToRequest(req, token) : req;

      return next(authReq).pipe(
        catchError((error: HttpErrorResponse) => {
          // Se for 401 (não autorizado), tentar refresh
          if (error.status === 401) {
            return handle401Error(req, next, store, router, authApiService);
          }
          return throwError(() => error);
        })
      );
    })
  );
};

function addTokenToRequest(req: HttpRequest<unknown>, token: string): HttpRequest<unknown> {
  return req.clone({
    setHeaders: {
      Authorization: `Bearer ${token}`
    }
  });
}

function handle401Error(
  req: HttpRequest<unknown>,
  next: HttpHandlerFn,
  store: Store,
  router: Router,
  authApiService: AuthApiService
) {
  // Se já estiver fazendo refresh, aguardar
  if (isRefreshing) {
    return refreshTokenSubject.pipe(
      filter(token => token !== null),
      take(1),
      switchMap(token => {
        return next(addTokenToRequest(req, token!));
      })
    );
  }

  isRefreshing = true;
  refreshTokenSubject.next(null);

  // Pegar refresh token e user atual do store
  return combineLatest([
    store.select(selectRefreshToken),
    store.select(selectUser)
  ]).pipe(
    first(),
    switchMap(([refreshToken, currentUser]) => {
      if (!refreshToken) {
        // Sem refresh token, fazer logout
        return handleLogout(store, router);
      }

      return authApiService.refresh(refreshToken).pipe(
        switchMap((response: any) => {
          isRefreshing = false;

          if (response && response.accessToken) {
            // Atualizar tokens no store, preservando user se não vier na resposta
            store.dispatch(AuthActions.refreshTokenSuccess({
              auth: {
                isAuthenticated: true,
                accessToken: response.accessToken,
                refreshToken: response.refreshToken || refreshToken,
                user: response.user || currentUser,
                error: null
              }
            }));

            // Notificar outras requisições aguardando
            refreshTokenSubject.next(response.accessToken);

            // Repetir a requisição original com novo token
            return next(addTokenToRequest(req, response.accessToken));
          }

          // Resposta inválida, fazer logout
          return handleLogout(store, router);
        }),
        catchError((refreshError: HttpErrorResponse) => {
          isRefreshing = false;
          console.error('Erro ao fazer refresh do token:', refreshError);

          // So desloga se o servidor disse explicitamente que o refresh token nao vale (401/403).
          // Erros de rede/servidor (status 0, 5xx) nao devem invalidar a sessao.
          const isAuthRejection = refreshError?.status === 401 || refreshError?.status === 403;
          if (isAuthRejection) {
            store.dispatch(AuthActions.refreshTokenFailure({ error: refreshError }));
            return handleLogout(store, router);
          }

          // Erro transiente: libera as requisicoes em espera com erro, mantem a sessao.
          const failed = refreshTokenSubject;
          resetRefreshSubject();
          failed.error(refreshError);
          return throwError(() => refreshError);
        })
      );
    })
  );
}

function handleLogout(store: Store, router: Router) {
  isRefreshing = false;
  // Emit empty string to unblock any waiting requests (they will fail)
  refreshTokenSubject.next('');

  store.dispatch(AuthActions.logout());
  router.navigate(['/auth/login']);

  return throwError(() => new HttpErrorResponse({
    status: 401,
    statusText: 'Sessao expirada. Por favor, faca login novamente.'
  }));
}
