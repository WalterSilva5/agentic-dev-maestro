import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AppConfigApiService, AppConfigDto } from '../../services/app-config.service';
import Swal from 'sweetalert2';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './settings.component.html',
  styleUrl: './settings.component.scss'
})
export class SettingsComponent implements OnInit {
  configs: AppConfigDto[] = [];
  loading = true;
  saving = false;

  // Configurações de exemplo com valores editáveis
  dailyGlobalLimit = 100;
  dailyUserLimit = 10;
  featureEnabled = true;

  constructor(private configService: AppConfigApiService) {}

  ngOnInit() {
    this.loadConfigs();
  }

  async loadConfigs() {
    this.loading = true;
    try {
      this.configs = await this.configService.getAll();

      // Extrair valores específicos
      this.dailyGlobalLimit = this.getConfigValue('DAILY_REQUEST_LIMIT', 100);
      this.dailyUserLimit = this.getConfigValue('DAILY_REQUEST_LIMIT_PER_USER', 10);
      this.featureEnabled = this.getConfigValue('EXAMPLE_FEATURE_ENABLED', 'true') === 'true';

    } catch (error) {
      console.error('Error loading configs:', error);
      Swal.fire({
        icon: 'error',
        title: 'Erro',
        text: 'Erro ao carregar configurações. Verifique se você tem permissão de administrador.'
      });
    } finally {
      this.loading = false;
    }
  }

  private getConfigValue(key: string, defaultValue: any): any {
    const config = this.configs.find(c => c.key === key);
    return config?.value ?? defaultValue;
  }

  async saveConfigs() {
    this.saving = true;
    try {
      const configsToUpdate: AppConfigDto[] = [
        {
          key: 'DAILY_REQUEST_LIMIT',
          value: this.dailyGlobalLimit.toString(),
          description: 'Limite diário global de requisições (exemplo)',
          type: 'number'
        },
        {
          key: 'DAILY_REQUEST_LIMIT_PER_USER',
          value: this.dailyUserLimit.toString(),
          description: 'Limite diário de requisições por usuário (exemplo)',
          type: 'number'
        },
        {
          key: 'EXAMPLE_FEATURE_ENABLED',
          value: this.featureEnabled.toString(),
          description: 'Habilitar/desabilitar funcionalidade de exemplo',
          type: 'boolean'
        }
      ];

      await this.configService.updateMany(configsToUpdate);

      Swal.fire({
        icon: 'success',
        title: 'Sucesso!',
        text: 'Configurações salvas com sucesso.',
        timer: 2000,
        showConfirmButton: false
      });

    } catch (error) {
      console.error('Error saving configs:', error);
      Swal.fire({
        icon: 'error',
        title: 'Erro',
        text: 'Erro ao salvar configurações.'
      });
    } finally {
      this.saving = false;
    }
  }
}
