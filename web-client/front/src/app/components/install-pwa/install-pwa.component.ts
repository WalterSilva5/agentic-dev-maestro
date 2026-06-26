import { Component, OnInit, Inject, PLATFORM_ID } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { PlatformService } from '../../services/platform.service';

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

@Component({
  selector: 'app-install-pwa',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="install-pwa-container" *ngIf="showInstallButton">
      <button class="install-pwa-button" (click)="installPwa()">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="7 10 12 15 17 10"></polyline>
          <line x1="12" y1="15" x2="12" y2="3"></line>
        </svg>
        Instalar App
      </button>
      <button class="close-install-button" (click)="dismissInstall()" title="Fechar">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    </div>
  `,
  styles: [`
    @use '../../../assets/styles/colors.scss' as *;

    .install-pwa-container {
      position: fixed;
      bottom: 20px;
      left: 50%;
      transform: translateX(-50%);
      z-index: 1000;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      background: #1DB954;
      padding: 0.5rem;
      border-radius: 50px;
      box-shadow: 0 8px 24px rgba(29, 185, 84, 0.4);
      animation: slideUp 0.4s ease-out;
    }

    @keyframes slideUp {
      from {
        transform: translateX(-50%) translateY(100px);
        opacity: 0;
      }
      to {
        transform: translateX(-50%) translateY(0);
        opacity: 1;
      }
    }

    .install-pwa-button {
      background: $white_1;
      color: $primary;
      border: none;
      padding: 0.75rem 1.5rem;
      border-radius: 50px;
      font-weight: 600;
      font-size: 0.95rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      transition: all 0.3s ease;

      svg {
        width: 20px;
        height: 20px;
      }

      &:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
      }

      &:active {
        transform: scale(0.98);
      }
    }

    .close-install-button {
      background: rgba(255, 255, 255, 0.2);
      border: none;
      width: 32px;
      height: 32px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: all 0.3s ease;

      svg {
        width: 16px;
        height: 16px;
        color: $white_1;
      }

      &:hover {
        background: rgba(255, 255, 255, 0.3);
      }
    }

    @media (max-width: 768px) {
      .install-pwa-container {
        bottom: 10px;
        left: 10px;
        right: 10px;
        transform: none;
      }

      .install-pwa-button {
        flex: 1;
        justify-content: center;
      }
    }
  `]
})
export class InstallPwaComponent implements OnInit {
  showInstallButton = false;
  private deferredPrompt: BeforeInstallPromptEvent | null = null;

  constructor(
    @Inject(PLATFORM_ID) private platformId: object,
    private platformService: PlatformService,
  ) {}

  ngOnInit(): void {
    if (!isPlatformBrowser(this.platformId) || this.platformService.isNative) {
      return;
    }

    // Verificar se já está instalado como PWA standalone
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches ||
                         (window.navigator as any).standalone === true;

    if (isStandalone) {
      console.log('App já está instalado e rodando como PWA');
      localStorage.removeItem('pwa-install-dismissed');
      localStorage.removeItem('pwa-install-dismissed-time');
      localStorage.setItem('pwa-installed', 'true');
      return;
    }

    // Verificar se já foi instalado anteriormente
    if (localStorage.getItem('pwa-installed') === 'true') {
      console.log('PWA já foi instalado anteriormente');
      return;
    }

    // Verificar se já foi rejeitado anteriormente (com expiração de 24 horas)
    const dismissedTime = localStorage.getItem('pwa-install-dismissed-time');
    if (dismissedTime) {
      const dismissedAt = parseInt(dismissedTime, 10);
      const now = Date.now();
      const hoursElapsed = (now - dismissedAt) / (1000 * 60 * 60);

      if (hoursElapsed < 24) {
        console.log(`PWA install dismissed há ${hoursElapsed.toFixed(1)} horas. Aguardando 24h.`);
        return;
      } else {
        localStorage.removeItem('pwa-install-dismissed');
        localStorage.removeItem('pwa-install-dismissed-time');
      }
    }

    // Escutar evento de instalação
    window.addEventListener('beforeinstallprompt', (e: Event) => {
      e.preventDefault();
      this.deferredPrompt = e as BeforeInstallPromptEvent;
      this.showInstallButton = true;
      console.log('PWA pode ser instalado!');
    });

    // Escutar quando for instalado
    window.addEventListener('appinstalled', () => {
      console.log('PWA instalado com sucesso!');
      this.showInstallButton = false;
      this.deferredPrompt = null;
      localStorage.setItem('pwa-installed', 'true');
      localStorage.removeItem('pwa-install-dismissed');
      localStorage.removeItem('pwa-install-dismissed-time');
    });
  }

  async installPwa(): Promise<void> {
    if (!this.deferredPrompt) {
      return;
    }

    await this.deferredPrompt.prompt();
    const { outcome } = await this.deferredPrompt.userChoice;

    console.log(`Usuário ${outcome === 'accepted' ? 'aceitou' : 'rejeitou'} a instalação`);

    if (outcome === 'accepted') {
      this.showInstallButton = false;
    }

    this.deferredPrompt = null;
  }

  dismissInstall(): void {
    this.showInstallButton = false;
    localStorage.setItem('pwa-install-dismissed', 'true');
    localStorage.setItem('pwa-install-dismissed-time', Date.now().toString());
  }
}
