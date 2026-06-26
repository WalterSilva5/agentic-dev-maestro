import { Injectable } from '@angular/core';
import { CanActivate, Router, UrlTree } from '@angular/router';
import { Store } from '@ngrx/store';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { AuthState } from '../state/auth/auth.models';
import { selectAuthState } from '../state/auth/auth.selectors';

@Injectable({
  providedIn: 'root'
})
export class AuthGuard implements CanActivate {
  private isNavigating = false;
  private static callCount = 0;

  constructor(private store: Store, private router: Router) {}

  canActivate(): Observable<boolean | UrlTree> {
    AuthGuard.callCount++;
    console.log(`[AuthGuard] canActivate called (call #${AuthGuard.callCount})`);

    return this.store.select(selectAuthState).pipe(
      map((authState: AuthState) => {
        console.log(`[AuthGuard] isAuthenticated: ${authState.isAuthenticated}`);

        if (authState.isAuthenticated) {
          this.isNavigating = false; // Reset flag on successful auth
          console.log('[AuthGuard] Allowing access');
          return true;
        } else {
          console.log('[AuthGuard] Redirecting to login via UrlTree');

          // Return UrlTree instead of imperatively navigating
          // This prevents multiple navigation attempts
          return this.router.createUrlTree(['/auth/login']);
        }
      })
    );
  }
}
