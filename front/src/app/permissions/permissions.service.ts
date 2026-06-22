import { Injectable } from '@angular/core';
import { Store } from '@ngrx/store';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { AuthState } from '../state/auth/auth.models';
import { selectUserRole } from '../state/auth/auth.selectors';
import { Roles } from '../state/roles/roles.enum';

@Injectable({
  providedIn: 'root'
})
export class PermissionService {
  constructor(private store: Store<{ auth: AuthState }>) {}

  /**
   * Verifica se o usuário tem permissão baseado na hierarquia de roles:
   * - ADMIN tem acesso a: ADMIN, MANAGER, USER
   * - MANAGER tem acesso a: MANAGER, USER
   * - USER tem acesso a: USER
   */
  hasPermission(allowedRoles: string[]): Observable<boolean> {
    return this.store.select(selectUserRole).pipe(
      map((userRole) => {
        if (!userRole) return false;

        // Obter todas as permissões que o usuário tem baseado na hierarquia
        const userPermissions = this.getUserPermissions(userRole);

        // Verificar se alguma das permissões do usuário está na lista de roles permitidos
        return allowedRoles.some(role => userPermissions.includes(role));
      })
    );
  }

  /**
   * Retorna todas as permissões que um usuário tem baseado no seu role hierárquico
   */
  private getUserPermissions(userRole: string): string[] {
    switch (userRole) {
      case Roles.ADMIN:
        return [Roles.ADMIN, Roles.MANAGER, Roles.USER];
      case Roles.MANAGER:
        return [Roles.MANAGER, Roles.USER];
      case Roles.USER:
        return [Roles.USER];
      default:
        return [];
    }
  }

  /**
   * Verifica se o usuário tem um role específico ou superior na hierarquia
   */
  hasRoleOrHigher(requiredRole: string): Observable<boolean> {
    return this.hasPermission([requiredRole]);
  }

  /**
   * Verifica se o usuário tem exatamente o role especificado (não hierárquico)
   */
  hasExactRole(exactRole: string): Observable<boolean> {
    return this.store.select(selectUserRole).pipe(
      map((userRole) => userRole === exactRole)
    );
  }
}
