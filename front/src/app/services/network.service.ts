import { Injectable, Inject, PLATFORM_ID, NgZone } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { BehaviorSubject, Observable } from 'rxjs';
import { Network } from '@capacitor/network';
import { PlatformService } from './platform.service';

@Injectable({
  providedIn: 'root',
})
export class NetworkService {
  private connected$ = new BehaviorSubject<boolean>(true);

  constructor(
    private platformService: PlatformService,
    private ngZone: NgZone,
    @Inject(PLATFORM_ID) private platformId: object,
  ) {
    if (isPlatformBrowser(this.platformId)) {
      this.init();
    }
  }

  get isConnected$(): Observable<boolean> {
    return this.connected$.asObservable();
  }

  get isConnected(): boolean {
    return this.connected$.value;
  }

  private async init(): Promise<void> {
    if (this.platformService.isNative) {
      const status = await Network.getStatus();
      this.connected$.next(status.connected);

      Network.addListener('networkStatusChange', (status) => {
        this.ngZone.run(() => this.connected$.next(status.connected));
      });
    } else {
      this.connected$.next(navigator.onLine);

      window.addEventListener('online', () => {
        this.ngZone.run(() => this.connected$.next(true));
      });
      window.addEventListener('offline', () => {
        this.ngZone.run(() => this.connected$.next(false));
      });
    }
  }
}
