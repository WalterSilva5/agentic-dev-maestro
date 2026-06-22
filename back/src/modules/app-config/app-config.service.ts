import { Injectable, Logger } from '@nestjs/common';
import { PrismaService } from 'src/database/prisma/prisma.service';

// Configurações padrão da aplicação (exemplos — ajuste ao seu projeto)
export const DEFAULT_CONFIGS = {
  APP_NAME: {
    key: 'APP_NAME',
    value: 'Fullstack Template',
    description: 'Nome exibido da aplicação',
    type: 'string',
  },
  MAINTENANCE_MODE: {
    key: 'MAINTENANCE_MODE',
    value: 'false',
    description: 'Coloca a aplicação em modo de manutenção',
    type: 'boolean',
  },
};

export interface AppConfigDto {
  key: string;
  value: string;
  description?: string;
  type?: string;
}

@Injectable()
export class AppConfigService {
  private readonly logger = new Logger(AppConfigService.name);

  constructor(private readonly prisma: PrismaService) {}

  async initializeDefaults(): Promise<void> {
    for (const config of Object.values(DEFAULT_CONFIGS)) {
      const existing = await this.prisma.appConfig.findUnique({
        where: { key: config.key },
      });

      if (!existing) {
        await this.prisma.appConfig.create({
          data: config,
        });
        this.logger.log(`Created default config: ${config.key}`);
      }
    }
  }

  async get(key: string): Promise<string | null> {
    const config = await this.prisma.appConfig.findUnique({
      where: { key },
    });
    return config?.value ?? null;
  }

  async getNumber(key: string): Promise<number | null> {
    const value = await this.get(key);
    if (value === null) return null;
    const num = parseInt(value, 10);
    return isNaN(num) ? null : num;
  }

  async getBoolean(key: string): Promise<boolean> {
    const value = await this.get(key);
    return value === 'true' || value === '1';
  }

  async set(key: string, value: string, description?: string, type?: string): Promise<void> {
    await this.prisma.appConfig.upsert({
      where: { key },
      update: { value, ...(description && { description }), ...(type && { type }) },
      create: { key, value, description, type: type || 'string' },
    });
    this.logger.log(`Config updated: ${key} = ${value}`);
  }

  async getAll(): Promise<AppConfigDto[]> {
    return this.prisma.appConfig.findMany({
      orderBy: { key: 'asc' },
    });
  }

  async updateMany(configs: AppConfigDto[]): Promise<void> {
    for (const config of configs) {
      await this.set(config.key, config.value, config.description, config.type);
    }
  }
}
