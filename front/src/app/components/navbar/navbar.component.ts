/* eslint-disable @typescript-eslint/no-empty-function */
/* eslint-disable @typescript-eslint/class-literal-property-style */
import * as AuthActions from '../../../app/state/auth/auth.actions';
import { CommonModule } from '@angular/common';
import { AuthState } from '../../state/auth/auth.models';
import { ChangeDetectionStrategy, Component, OnDestroy, OnInit, ElementRef, HostListener } from '@angular/core';
import { CreditsSyncService } from '../../services/credits-sync.service';
import { Observable, Subject, interval } from 'rxjs';
import { map, distinctUntilChanged, takeUntil, switchMap } from 'rxjs/operators';
import { Router, RouterModule } from '@angular/router';
import { Store } from '@ngrx/store';
import { selectAuth, selectAuthToken } from '../../../app/state/auth/auth.selectors';
import { PermissionService } from '../../permissions/permissions.service';
import { RoutesEnum } from '../../routes/routes.enum';
import { Roles } from '../../state/roles/roles.enum';
import { AuthApiHandler } from '../../pages/auth/data-handler/auth-api.handler';
import { TenantService, ActiveCompany } from '../../services/tenant.service';
import { WorkspaceService } from '../../services/workspace.service';

@Component({
  selector: 'app-navbar',
  host: {
    ngSkipHydration: ''
  },
  templateUrl: './navbar.component.html',
  styleUrls: ['./navbar.component.scss'],
  standalone: true,
  imports: [RouterModule, CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NavbarComponent implements OnInit, OnDestroy {
  menuItems: unknown[] = [];
  auth$: Observable<AuthState>;
  userBalance$!: Observable<number>;
  balanceLevel$!: Observable<'low' | 'medium' | 'high'>;

  canAccessUser$!: Observable<boolean>;
  canAccessSettings$!: Observable<boolean>;

  isMobileMenuOpen = false;
  isWorkspaceMenuOpen = false;

  isAdminDropdownOpen = false;
  private destroy$ = new Subject<void>();
  private userNameValue = '';
  private hasNavigatedToLogin = false;
  private authToken$!: Observable<string | null>;

  constructor(
    private router: Router,
    private store: Store<{ counter: number }>,
    private permissionService: PermissionService,
    private creditsSync: CreditsSyncService,
    private authApi: AuthApiHandler,
    public tenant: TenantService,
    private workspaces: WorkspaceService
    , private elementRef: ElementRef
  ) {
    this.auth$ = this.store.select(selectAuth);
    this.authToken$ = this.store.select(selectAuthToken);
    this.userBalance$ = this.auth$.pipe(map((a) => a?.user?.creditAccount?.balance ?? 0));
    this.balanceLevel$ = this.userBalance$.pipe(
      map((b) => (b <= 0 ? 'low' : b < 50 ? 'medium' : 'high'))
    );
  }

  onNavFocusIn(_event: FocusEvent): void {
    // noop for now; method exists so template binding compiles
  }

  onNavFocusOut(event: FocusEvent): void {
    // Close mobile menu when focus moves outside the nav (mobile only)
    try {
      if (!this.isMobileMenuOpen) return;
      if (typeof window !== 'undefined' && window.innerWidth >= 768) return; // only on small screens

      const related = event.relatedTarget as Node | null;
      if (!related || !this.elementRef.nativeElement.contains(related)) {
        this.closeMobileMenu();
      }
    } catch (e) {
      console.warn('Error handling nav focus out:', e);
    }
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    try {
      if (!this.isMobileMenuOpen) return;
      if (typeof window !== 'undefined' && window.innerWidth >= 768) return; // only on small screens

      const target = event.target as Node;
      if (!this.elementRef.nativeElement.contains(target)) {
        this.closeMobileMenu();
      }
    } catch (e) {
      console.warn('Error handling document click for navbar:', e);
    }
  }

  ngOnInit(): void {
    this.canAccessUser$ = this.permissionService.hasPermission([Roles.ADMIN]);
    this.canAccessSettings$ = this.permissionService.hasPermission([Roles.ADMIN]);

    this.creditsSync.start({ intervalMs: 60_000 });

    // Atualiza dados do usuario ao logar e a cada 5min.
    // Refresh do access token e responsabilidade exclusiva do auth.interceptor (reativo em 401).
    this.authToken$
      .pipe(
        switchMap((token) => {
          if (!token) {
            return new Observable((observer) => observer.complete());
          }
          this.refreshUserData(token);
          return interval(300_000).pipe(
            switchMap(() => this.refreshUserData(token))
          );
        }),
        takeUntil(this.destroy$)
      )
      .subscribe();

    this.auth$
      .pipe(
        distinctUntilChanged((a, b) => a?.isAuthenticated === b?.isAuthenticated),
        takeUntil(this.destroy$)
      )
      .subscribe((auth) => {
        const firstName = auth?.user?.firstName || '';
        const lastName = auth?.user?.lastName || '';
        this.userNameValue = `${firstName} ${lastName}`.trim();
        // Popula o seletor de workspaces quando autenticado.
        if (auth?.isAuthenticated) {
          this.workspaces.refresh().catch(() => undefined);
        }
      });
  }

  private async refreshUserData(token: string): Promise<void> {
    try {
      const userData = await this.authApi.getMe(token);
      if (userData) {
        this.store.dispatch(AuthActions.updateUserSuccess({ user: userData }));
      }
    } catch (error) {
      console.warn('Erro ao atualizar dados do usuário:', error);
    }
  }

  ngOnDestroy(): void {
    this.creditsSync.stop();
    this.destroy$.next();
    this.destroy$.complete();
  }
  get currentBaseRouteIsAuth(): boolean {
    const currentUrl = this.router.url;
    return (
      currentUrl.startsWith('/auth') ||
      currentUrl === '/' ||
      currentUrl === `/${RoutesEnum.LOGIN}` ||
      currentUrl === `/${RoutesEnum.GOOGLE_CALLBACK}` ||
      currentUrl.includes(RoutesEnum.LOGIN) ||
      currentUrl.includes(RoutesEnum.GOOGLE_CALLBACK)
    );
  }

  get currentRouteIsAuth(): boolean {
    const currentUrl = this.router.url;
    return currentUrl.startsWith('/auth')
  }

  get userName(): string {
    return this.userNameValue;
  }

  logout(): void {
    this.store.dispatch(AuthActions.logout());
  }

  get logoutIcon(): string {
    return '/icons/icon_exit.svg';
  }

  get userIcon(): string {
    return '/icons/icon_user.svg';
  }
  get pipeIcon(): string {
    return '/icons/General/Other1.svg';
  }

  truncateName(): string {
    const oringinalName = this.userName;
    let name = oringinalName.substring(0, 10);
    if (oringinalName.length > 10) {
      name += '...';
    }
    return name;
  }

  async handleLogout(): Promise<void> {
    this.logout();
    this.tenant.clear();
    this.router.navigate([RoutesEnum.LOGIN]);
  }

  // ---- Seletor de workspace ----
  toggleWorkspaceMenu(): void {
    this.isWorkspaceMenuOpen = !this.isWorkspaceMenuOpen;
  }

  switchWorkspace(ws: ActiveCompany): void {
    this.isWorkspaceMenuOpen = false;
    this.closeMobileMenu();
    if (this.tenant.companyId === ws.id) return;
    this.tenant.setActive(ws);
    // Recarrega a visão no contexto do novo workspace.
    this.router.navigate([RoutesEnum.PROJECTS]);
  }

  goToWorkspaces(): void {
    this.isWorkspaceMenuOpen = false;
    this.closeMobileMenu();
    this.router.navigate([RoutesEnum.COMPANIES]);
  }

  toggleMobileMenu(): void {
    this.isMobileMenuOpen = !this.isMobileMenuOpen;
    console.log('Menu mobile toggled:', this.isMobileMenuOpen);

    if (!this.isMobileMenuOpen) {
      this.isAdminDropdownOpen = false;
    }
  }

  closeMobileMenu(): void {
    this.isMobileMenuOpen = false;
    this.isAdminDropdownOpen = false;
    console.log('Menu mobile closed');
  }

  toggleAdminDropdown(): void {
    this.isAdminDropdownOpen = !this.isAdminDropdownOpen;
    console.log('Admin dropdown toggled:', this.isAdminDropdownOpen);
  }

  goToProfile(): void {
    try {
      this.closeMobileMenu();
      this.router.navigate([RoutesEnum.USER_PROFILE]);
    } catch (e) {
      console.warn('Erro ao navegar para perfil:', e);
    }
  }

  onNavigate(): void {
    this.closeMobileMenu();
  }

  async loadData(): Promise<void> {}

  async checkMaintenanceMode(): Promise<void> {}
}
