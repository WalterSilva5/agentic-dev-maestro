import { Injectable } from '@angular/core';
import { CanActivate, ActivatedRouteSnapshot, RouterStateSnapshot, Router } from '@angular/router';
import { Store } from '@ngrx/store';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { AuthState } from '../state/auth/auth.models';
import { selectAuthState } from '../state/auth/auth.selectors';
@Injectable({
  providedIn: 'root'
})
export class PermissionsGuard implements CanActivate {
  constructor(private store: Store, private router: Router) {}

  canActivate(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ): Observable<boolean> {
    const requiredRoles: string[] = route.data['requiredRoles'];

    return this.store.select(selectAuthState).pipe(
      map((authState: AuthState) => {
        if (authState.isAuthenticated && requiredRoles.includes(authState.user?.role || '')) {
          return true;
        } else {
          //TODO create a forbidden page
          console.error('Not authorized');
          this.router.navigate(['/home']);
          return false;
        }
      })
    );
  }
}
