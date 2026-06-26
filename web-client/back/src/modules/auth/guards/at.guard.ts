import type { ExecutionContext } from '@nestjs/common';
import { Injectable, Logger, UnauthorizedException } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { AuthGuard } from '@nestjs/passport';
import { ROLES_KEY } from 'src/decorators/role.decorator';
import { IS_PUBLIC_KEY } from 'src/decorators/unprotected.decorator';
import type { IAuthRequest } from 'src/interfaces/IAuthRequest';
import { UserActivityRegistry } from 'src/modules/user/user.registry';
@Injectable()
export class AtGuard extends AuthGuard('jwt') {
  _logger = new Logger(AtGuard.name);
  constructor(
    private reflector: Reflector,
    private userActivityRegistry: UserActivityRegistry
  ) {
    super();
  }

  async canActivate(context: ExecutionContext) {
    const unprotected = this.getReflector(IS_PUBLIC_KEY, context);
    this._logger.debug(`Unprotected route: ${unprotected}`);
    if (unprotected) return true;
    this._logger.debug(`Protected route, checking authentication...`);

    // First, call the original AuthGuard's canActivate method
    const canActivate = super.canActivate(context);

    if (typeof canActivate === 'boolean') {
      this._logger.debug(`canActivate returned boolean: ${canActivate}`);
      return canActivate;
    }

    const canActivatePromise = canActivate as Promise<boolean>;

    return canActivatePromise
      .then(async (result) => {
        this._logger.debug(`AuthGuard canActivate result: ${result}`);
        if (result == false) {
          this._logger.debug(`Authentication failed`);
          return false;
        }
        this._logger.debug(`Authentication successful, validating roles...`);
        return this.validateRoles(context);
      })
      .catch((error: unknown) => {
        this._logger.error(`Authentication error:`, error);
        throw new UnauthorizedException();
      });
  }

  getReflector<T = boolean>(metadataKey: string, context: ExecutionContext) {
    return this.reflector.getAllAndOverride<T>(metadataKey, [
      context.getHandler(),
      context.getClass()
    ]);
  }

  validateRoles(context: ExecutionContext): boolean {
    const roles = this.getReflector<string[]>(ROLES_KEY, context);
    const user = context.switchToHttp().getRequest<IAuthRequest>().user;

    this.logValidationInfo(roles, user);

    if (!roles) {
      this._logger.debug(`No roles required, access granted`);
      return true;
    }

    if (!user) {
      this._logger.debug(`No user found in request, access denied`);
      return false;
    }

    this.userActivityRegistry.registerActivity(`${user.id}`);

    const hasRequiredRole = roles.includes(user.role);
    if (hasRequiredRole) {
      this._logger.debug(`User role ${user.role} matches required roles, access granted`);
      return true;
    }

    this.logAccessDenied(user, roles);
    return false;
  }

  private logValidationInfo(
    roles: string[] | undefined,
    user: IAuthRequest['user']
  ): void {
    this._logger.debug(
      `Validating roles - Required roles: ${roles ? roles.join(', ') : 'none'}`
    );
    this._logger.debug(
      `User from request: ${
        user ? `ID: ${user.id}, Email: ${user.email}, Role: ${user.role}` : 'null'
      }`
    );
  }

  private logAccessDenied(user: IAuthRequest['user'], roles: string[]): void {
    this._logger.error(`
      \rAcesso negado para: ${user.email}
      \rPermissões necessárias: [${roles.join(', ')}]
      \rPermissões atuais: [${user.role}]
    `);
  }
}
