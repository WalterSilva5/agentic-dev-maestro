import { ApplicationConfig, provideZoneChangeDetection, isDevMode } from '@angular/core';
import { provideRouter, withComponentInputBinding, withInMemoryScrolling } from '@angular/router';
import { routes } from './routes/app.routes';
import { provideHttpClient, withFetch, withInterceptors } from '@angular/common/http';
import { provideStore } from '@ngrx/store';
import { provideEffects } from '@ngrx/effects';
import { provideStoreDevtools } from '@ngrx/store-devtools';
import { provideRouterStore } from '@ngrx/router-store';
import { authReducer } from './state/auth/auth.reducer';
import { authInterceptor } from './modules/interceptors/auth.interceptor';
import { CONFIG_INITIALIZER_PROVIDER } from './config/config.initializer';


const isDev = isDevMode();

export const appConfig: ApplicationConfig = {
  providers: [
    CONFIG_INITIALIZER_PROVIDER,
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes, withComponentInputBinding(), withInMemoryScrolling({
      scrollPositionRestoration: 'enabled'
    })),
    provideHttpClient(withFetch(), withInterceptors([authInterceptor])),
    provideStore({ auth: authReducer }),
    provideEffects(),
    provideStoreDevtools({ maxAge: 25, logOnly: isDev }),
    provideRouterStore(),
  ],
};
