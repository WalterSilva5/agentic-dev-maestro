import { Component, OnInit, Inject, inject } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { Store } from '@ngrx/store';
import { AppState } from '../../../state';
import * as AuthActions from '../../../state/auth/auth.actions';
import { AuthState } from '../../../state/auth/auth.models';
import { AuthApiHandler } from '../data-handler/auth-api.handler';
import { ConfigService } from '../../../services/config.service';
import { PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { take } from 'rxjs/operators';

@Component({
  selector: 'app-google-callback',
  standalone: true,
  template: '<p>Processando login com Google...</p>',
})
export class GoogleCallbackComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private store: Store<AppState> = inject(Store);
  private api = inject(AuthApiHandler);
  private configService = inject(ConfigService);
  @Inject(PLATFORM_ID) private platformId: object = inject(PLATFORM_ID);

  async ngOnInit() {
    console.log('GoogleCallbackComponent initialized');
    if (!isPlatformBrowser(this.platformId)) {
      console.log('GoogleCallbackComponent: not running in browser, skipping');
      return;
    }

    console.log('GoogleCallbackComponent subscribing to queryParams');
    this.route.queryParams.pipe(take(1)).subscribe(async (params) => {
      const code = params['code'];
      const accessToken = params['access'];
      const refreshToken = params['refresh'];

      if (code) {
        console.log('GoogleCallbackComponent code received:', code);
        try {
          window.location.href = `${this.configService.apiUrl}/auth/accounts/google/redirect?code=${code}`;
        } catch (e) {
          console.error('Redirecionamento falhou', e);
          this.router.navigate(['/auth/login']);
        }
        return;
      }

      if (accessToken && refreshToken) {
        try {
          const profile = await this.api.getMe(accessToken);
          console.log('Fetched profile:', profile);
          const auth: AuthState = {
            isAuthenticated: true,
            accessToken,
            refreshToken,
            user: profile,
            error: null,
          };
          this.store.dispatch(AuthActions.loginSuccess({ auth }));
          this.router.navigate(['/home']);
        } catch (error) {
          console.error('Failed to fetch profile', error);
          this.router.navigate(['/auth/login']);
        }
      } else {
        console.log('GoogleCallbackComponent: no code or tokens found, redirecting to login');
        this.router.navigate(['/auth/login']);
      }
    });
  }
}
