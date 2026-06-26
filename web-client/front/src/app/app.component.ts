import { Component, OnInit, isDevMode, PLATFORM_ID, Inject, HostBinding } from '@angular/core';
import { isPlatformBrowser, CommonModule } from '@angular/common';
import { Router, RouterEvent, RouterModule, RouterOutlet } from '@angular/router';
import { NavbarComponent } from './components/navbar/navbar.component';
import { MobileBottomNavComponent } from './components/mobile-bottom-nav/mobile-bottom-nav.component';
import { InstallPwaComponent } from './components/install-pwa/install-pwa.component';
import { DataService } from './modules/data-service/data.service';
import { OfflineBannerComponent } from './components/offline-banner/offline-banner.component';
import { PlatformService } from './services/platform.service';
import { ConfigService } from './services/config.service';
import { App as CapacitorApp } from '@capacitor/app';
import { StatusBar, Style } from '@capacitor/status-bar';
import { SplashScreen } from '@capacitor/splash-screen';
import { Keyboard } from '@capacitor/keyboard';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
  imports: [
    RouterOutlet,
    NavbarComponent,
    MobileBottomNavComponent,
    InstallPwaComponent,
    OfflineBannerComponent,
    RouterModule,
    CommonModule,
  ],
})
export class AppComponent implements OnInit {
  title = 'wsi';
  data: unknown;
  @HostBinding('class.with-navbar')
  showNavbar = true;
  private static initCount = 0;
  private routerEventsSub?: { unsubscribe: () => void };

  constructor(
    private dataService: DataService,
    private router: Router,
    private platformService: PlatformService,
    private configService: ConfigService,
    @Inject(PLATFORM_ID) private platformId: object
  ) {
    // Only run in browser (not in SSR)
    if (isPlatformBrowser(this.platformId)) {
      // Catch unhandled promise rejections
      window.addEventListener('unhandledrejection', (event) => {
        console.error('[AppComponent] Unhandled promise rejection:', event.reason);
        event.preventDefault(); // Prevent default behavior
      });

      // Catch global errors
      window.addEventListener('error', (event) => {
        console.error('[AppComponent] Global error:', event.error);
      });
    }
  }

  ngOnInit(): void {
    AppComponent.initCount++;
    const currentUrl = this.router.url;

    // Verificar a rota atual e ocultar navbar em páginas de autenticação
    this.checkRoute(currentUrl);

    // EMERGENCY STOP: Prevent infinite loop
    if (AppComponent.initCount > 5) {
      console.error(`🛑 EMERGENCY STOP! AppComponent initialized ${AppComponent.initCount} times. Blocking further execution.`);
      return; // Stop execution immediately
    }

    // Log router events to diagnose endless navigations
    if (!this.routerEventsSub) {
      this.routerEventsSub = this.router.events.subscribe((evt: unknown) => {
        const routerEvent = evt as RouterEvent;
        const type = routerEvent?.constructor?.name;

        // Atualizar visibilidade do navbar ao navegar
        if (type === 'NavigationEnd') {
          this.checkRoute(this.router.url);
        }

        // Limit noise
        if (type === 'NavigationStart' || type === 'NavigationEnd' || type === 'NavigationCancel' || type === 'NavigationError') {
          console.log(`[Router] ${type}:`, evt);
        }
      });
    }

    if (isDevMode()) {
      console.log(`[${new Date().toISOString()}] app-component ~ Development! (init #${AppComponent.initCount}) - URL: ${currentUrl}`);
      if (AppComponent.initCount > 3) {
        console.error('⚠️  LOOP DETECTED! AppComponent initialized more than 3 times.');
        console.trace('Stack trace:');
      }
    } else {
      console.log('app-component ~ Production!');
    }

    // Capacitor native platform setup
    if (isPlatformBrowser(this.platformId) && this.platformService.isNative) {
      this.initCapacitor();
    }
  }

  private async initCapacitor(): Promise<void> {
    try {
      // Status bar - use colors from config
      const statusBarColor = this.configService.appConfig?.theme?.statusBarColor ?? '#181818';
      await StatusBar.setBackgroundColor({ color: statusBarColor });
      await StatusBar.setStyle({ style: Style.Dark });

      // Handle Android back button
      CapacitorApp.addListener('backButton', ({ canGoBack }) => {
        if (canGoBack) {
          window.history.back();
        } else {
          CapacitorApp.exitApp();
        }
      });

      // Keyboard handling - scroll into view when input focused
      Keyboard.addListener('keyboardWillShow', () => {
        document.body.classList.add('keyboard-open');
      });
      Keyboard.addListener('keyboardWillHide', () => {
        document.body.classList.remove('keyboard-open');
      });

      // Hide splash screen after app is ready
      await SplashScreen.hide();
    } catch (error) {
      console.error('[Capacitor] Init error:', error);
    }
  }

  private checkRoute(url: string): void {
    // Ocultar navbar em rotas de autenticação e páginas públicas
    const hideNavbarRoutes = [
      '/auth/login',
      '/auth/register',
      '/auth/forgot-password',
      '/auth/reset-password',
      '/auth/google/callback'
    ];
    this.showNavbar = !hideNavbarRoutes.some(route => url.includes(route));
  }
}
