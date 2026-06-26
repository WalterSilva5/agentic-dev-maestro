import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';
import { NetworkService } from '../../services/network.service';

@Component({
  selector: 'app-offline-banner',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="offline-banner" *ngIf="isOffline">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="1" y1="1" x2="23" y2="23"></line>
        <path d="M16.72 11.06A10.94 10.94 0 0119 12.55"></path>
        <path d="M5 12.55a10.94 10.94 0 015.17-2.39"></path>
        <path d="M10.71 5.05A16 16 0 0122.56 9"></path>
        <path d="M1.42 9a15.91 15.91 0 014.7-2.88"></path>
        <path d="M8.53 16.11a6 6 0 016.95 0"></path>
        <line x1="12" y1="20" x2="12.01" y2="20"></line>
      </svg>
      <span>Sem conexao - modo offline</span>
    </div>
  `,
  styles: [`
    .offline-banner {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      z-index: 9999;
      background: #dc2626;
      color: white;
      padding: 8px 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      font-size: 0.85rem;
      font-weight: 500;
      padding-top: calc(8px + env(safe-area-inset-top, 0px));

      svg {
        width: 16px;
        height: 16px;
        flex-shrink: 0;
      }
    }
  `],
})
export class OfflineBannerComponent implements OnInit, OnDestroy {
  isOffline = false;
  private sub?: Subscription;

  constructor(private networkService: NetworkService) {}

  ngOnInit(): void {
    this.sub = this.networkService.isConnected$.subscribe(
      (connected) => (this.isOffline = !connected),
    );
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }
}
