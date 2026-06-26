import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ConfigService } from './config.service';
import { firstValueFrom } from 'rxjs';

export interface AppConfigDto {
  key: string;
  value: string;
  description?: string;
  type?: string;
}

export interface AILimitsDto {
  globalLimit: number;
  globalUsage: number;
  userLimit: number;
  userUsage: number;
  aiEnabled: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class AppConfigApiService {
  private get apiUrl(): string {
    return `${this.configService.apiUrl}/app-config`;
  }

  constructor(
    private http: HttpClient,
    private configService: ConfigService
  ) {}

  async getAll(): Promise<AppConfigDto[]> {
    return firstValueFrom(
      this.http.get<AppConfigDto[]>(this.apiUrl)
    );
  }

  async updateMany(configs: AppConfigDto[]): Promise<{ success: boolean }> {
    return firstValueFrom(
      this.http.put<{ success: boolean }>(this.apiUrl, configs)
    );
  }

  async getAILimits(): Promise<AILimitsDto> {
    return firstValueFrom(
      this.http.get<AILimitsDto>(`${this.apiUrl}/ai-limits`)
    );
  }
}
