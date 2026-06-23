import {
  Component,
  ChangeDetectionStrategy,
  HostListener,
  OnInit,
  OnDestroy
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule, NavigationEnd } from '@angular/router';
import { Store } from '@ngrx/store';
import { Observable, Subject, filter, takeUntil } from 'rxjs';
import { selectAuth, selectIsLoggedIn } from '../../state/auth/auth.selectors';
import * as AuthActions from '../../state/auth/auth.actions';

interface NavItem {
  icon: string;
  activeIcon: string;
  label: string;
  route: string;
  exactMatch?: boolean;
}

@Component({
  selector: 'app-mobile-bottom-nav',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './mobile-bottom-nav.component.html',
  styleUrls: ['./mobile-bottom-nav.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class MobileBottomNavComponent implements OnInit, OnDestroy {
  isMenuOpen = false;
  currentRoute = '';
  private destroy$ = new Subject<void>();

  isAuthenticated$: Observable<boolean>;
  auth$: Observable<any>;

  navItems: NavItem[] = [
    {
      icon: '/icons/home.svg',
      activeIcon: '/icons/home-filled.svg',
      label: 'Home',
      route: '/home',
      exactMatch: true
    },
    {
      icon: '/icons/icon-project.svg',
      activeIcon: '/icons/icon-project.svg',
      label: 'Projetos',
      route: '/projects'
    },
    {
      icon: '/icons/General/User.svg',
      activeIcon: '/icons/General/User.svg',
      label: 'Perfil',
      route: '/user/profile'
    }
  ];

  menuItems = [
    { icon: '/icons/General/User.svg', label: 'Meu Perfil', route: '/user/profile' },
    { icon: '/icons/icon-project.svg', label: 'Dashboard', route: '/dashboard' },
    { icon: '/icons/icon-project.svg', label: 'Projetos', route: '/projects' },
    { icon: '/icons/Communication/Group.svg', label: 'Membros', route: '/members' },
    { icon: '/icons/icon-project.svg', label: 'Labels', route: '/labels' },
    { icon: '/icons/General/Settings.svg', label: 'Acesso', route: '/access' },
    { icon: '/icons/icon-project.svg', label: 'API keys', route: '/api-keys' },
    { icon: '/icons/icon-project.svg', label: 'Workspaces', route: '/companies' },
    { icon: '/icons/icon-project.svg', label: 'Downloads', route: '/downloads' },
  ];

  adminMenuItems = [
    { icon: '/icons/Communication/Group.svg', label: 'Usuarios', route: '/user' },
    { icon: '/icons/General/Settings.svg', label: 'Configuracoes', route: '/settings' }
  ];

  constructor(
    private store: Store,
    private router: Router
  ) {
    this.isAuthenticated$ = this.store.select(selectIsLoggedIn);
    this.auth$ = this.store.select(selectAuth);
  }

  ngOnInit(): void {
    this.router.events
      .pipe(
        filter((event): event is NavigationEnd => event instanceof NavigationEnd),
        takeUntil(this.destroy$)
      )
      .subscribe((event) => {
        this.currentRoute = event.urlAfterRedirects;
        this.closeMenu();
      });

    this.currentRoute = this.router.url;
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  isActive(route: string, exactMatch = false): boolean {
    if (exactMatch) {
      return this.currentRoute === route || this.currentRoute === '/';
    }
    return this.currentRoute.startsWith(route);
  }

  toggleMenu(): void {
    this.isMenuOpen = !this.isMenuOpen;
  }

  closeMenu(): void {
    this.isMenuOpen = false;
  }

  navigate(route: string): void {
    this.router.navigate([route]);
    this.closeMenu();
  }

  logout(): void {
    this.store.dispatch(AuthActions.logout());
    this.closeMenu();
    this.router.navigate(['/auth/login']);
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    const target = event.target as HTMLElement;
    const isInsideMenu = target.closest('.mobile-menu-drawer');
    const isMenuButton = target.closest('.menu-toggle-btn');

    if (this.isMenuOpen && !isInsideMenu && !isMenuButton) {
      this.closeMenu();
    }
  }

  @HostListener('document:keydown.escape')
  onEscapeKey(): void {
    this.closeMenu();
  }

  isAdmin(auth: any): boolean {
    return auth?.user?.role === 'ADMIN' || auth?.user?.role === 'MANAGER';
  }
}
