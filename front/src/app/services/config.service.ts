import { Injectable } from '@angular/core';
import { AppConfig, AppMobileConfig } from '../models/app-config.interface';

/**
 * Serviço para gerenciar configurações da aplicação carregadas em runtime.
 * As configurações são carregadas do arquivo config.json em public/
 */
@Injectable({
  providedIn: 'root'
})
export class ConfigService {
  private config: AppConfig | null = null;

  /**
   * Carrega as configurações do arquivo config.json
   * Deve ser chamado antes do bootstrap da aplicação
   */
  async loadConfig(): Promise<AppConfig> {
    if (this.config) {
      return this.config;
    }

    try {
      const response = await fetch('/config.json');
      
      if (!response.ok) {
        throw new Error(`Failed to load config: ${response.statusText}`);
      }
      
      this.config = await response.json();
      return this.config as AppConfig;
    } catch (error) {
      console.error('Error loading config:', error);
      // TODO: Ajustar os valores de fallback conforme o ambiente de execução
      const defaultConfig: AppConfig = {
        // TODO: substituir por `apiUrl` real do ambiente de desenvolvimento quando aplicável
        apiUrl: 'http://localhost:3000/api',
        // Em fallback consideramos `production: false` para manter logs e debugging
        production: false,
      };

      // Aplicar fallback para permitir que a aplicação continue carregando.
      // Isso evita que a inicialização falhe quando `config.json` estiver ausente.
      this.config = defaultConfig;
      console.warn('Using default config fallback — replace with environment config.json for production.');
      return this.config as AppConfig;
    }
  }

  /**
   * Retorna a configuração atual
   * @throws Error se a configuração não foi carregada
   */
  getConfig(): AppConfig {
    if (!this.config) {
      throw new Error('Config not loaded. Call loadConfig() first.');
    }
    return this.config;
  }

  /**
   * Retorna a URL da API
   */
  get apiUrl(): string {
    return this.getConfig().apiUrl;
  }

  /**
   * Retorna se está em modo de produção
   */
  get isProduction(): boolean {
    return this.getConfig().production;
  }

  get appConfig(): AppMobileConfig | undefined {
    return this.getConfig().app;
  }
}
