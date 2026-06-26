import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import Swal from 'sweetalert2';

import { MaestroApiService } from '../../services/maestro-api.service';
import { TenantService } from '../../services/tenant.service';
import { Project } from '../../models/maestro.models';

@Component({
  selector: 'app-projects',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './projects.component.html',
  styleUrls: ['./projects.component.scss'],
})
export class ProjectsComponent implements OnInit {
  projects: Project[] = [];
  loading = false;

  // formulário de criação
  newName = '';
  newKey = '';
  newDescription = '';
  saving = false;

  constructor(
    private api: MaestroApiService,
    protected tenant: TenantService
  ) {}

  async ngOnInit(): Promise<void> {
    if (this.tenant.companyId === null) return;
    await this.loadProjects();
  }

  get hasCompany(): boolean {
    return this.tenant.companyId !== null;
  }

  async loadProjects(): Promise<void> {
    this.loading = true;
    try {
      this.projects = await this.api.listProjects();
    } catch (err) {
      console.error('Erro ao listar projetos: ', err);
      Swal.fire({
        icon: 'error',
        title: 'Erro ao carregar projetos',
        text: 'Não foi possível carregar a lista de projetos.',
      });
    } finally {
      this.loading = false;
    }
  }

  // key: maiúscula, 2-20 alfanuméricos
  onKeyInput(value: string): void {
    this.newKey = (value || '').toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 20);
  }

  private isValidKey(key: string): boolean {
    return /^[A-Z0-9]{2,20}$/.test(key);
  }

  async createProject(): Promise<void> {
    const name = this.newName.trim();
    const key = this.newKey.trim().toUpperCase();
    const description = this.newDescription.trim();

    if (!name) {
      Swal.fire({ icon: 'warning', title: 'Nome obrigatório', text: 'Informe o nome do projeto.' });
      return;
    }
    if (!this.isValidKey(key)) {
      Swal.fire({
        icon: 'warning',
        title: 'Key inválida',
        text: 'A key deve ter de 2 a 20 caracteres alfanuméricos (A-Z, 0-9).',
      });
      return;
    }

    this.saving = true;
    try {
      await this.api.createProject(
        description ? { name, key, description } : { name, key }
      );
      this.newName = '';
      this.newKey = '';
      this.newDescription = '';
      await this.loadProjects();
      Swal.fire({
        icon: 'success',
        title: 'Projeto criado!',
        text: 'O projeto foi criado com sucesso.',
      });
    } catch (err) {
      console.error('Erro ao criar projeto: ', err);
      Swal.fire({
        icon: 'error',
        title: 'Erro ao criar projeto',
        text: 'Ocorreu um erro ao criar o projeto. Tente novamente.',
      });
    } finally {
      this.saving = false;
    }
  }
}
