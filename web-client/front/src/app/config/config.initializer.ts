import { APP_INITIALIZER } from '@angular/core';
import { ConfigService } from '../services/config.service';

/**
 * Factory para inicializar o ConfigService antes do bootstrap da aplicação
 */
export function initializeApp(configService: ConfigService) {
  return () => configService.loadConfig();
}

/**
 * Provider para inicialização da aplicação
 * Adicione este provider ao array de providers em app.config.ts
 */
export const CONFIG_INITIALIZER_PROVIDER = {
  provide: APP_INITIALIZER,
  useFactory: initializeApp,
  deps: [ConfigService],
  multi: true
};
