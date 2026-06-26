import { Injectable } from '@angular/core';
import { Capacitor } from '@capacitor/core';

@Injectable({
  providedIn: 'root',
})
export class PlatformService {
  get isNative(): boolean {
    return Capacitor.isNativePlatform();
  }

  get isAndroid(): boolean {
    return Capacitor.getPlatform() === 'android';
  }

  get isWeb(): boolean {
    return Capacitor.getPlatform() === 'web';
  }

  get platform(): string {
    return Capacitor.getPlatform();
  }
}
