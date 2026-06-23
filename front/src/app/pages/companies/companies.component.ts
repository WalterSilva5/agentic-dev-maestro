import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import Swal from 'sweetalert2';

import { MaestroApiService } from '../../services/maestro-api.service';
import { TenantService } from '../../services/tenant.service';
import { WorkspaceService } from '../../services/workspace.service';
import { Company } from '../../models/maestro.models';

@Component({
  selector: 'app-companies',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './companies.component.html',
  styleUrls: ['./companies.component.scss'],
})
export class CompaniesComponent implements OnInit {
  companies: Company[] = [];
  loading = false;

  // formulário de criação
  newName = '';
  newSlug = '';
  saving = false;

  constructor(
    private api: MaestroApiService,
    protected tenant: TenantService,
    private workspaces: WorkspaceService
  ) {}

  async ngOnInit(): Promise<void> {
    await this.loadCompanies();
  }

  async loadCompanies(): Promise<void> {
    this.loading = true;
    try {
      this.companies = await this.api.listCompanies();
    } catch (err) {
      console.error('Erro ao listar workspaces: ', err);
      Swal.fire({
        icon: 'error',
        title: 'Erro ao carregar workspaces',
        text: 'Não foi possível carregar a lista de workspaces.',
      });
    } finally {
      this.loading = false;
    }
  }

  roleOf(c: Company): string {
    return c.memberships?.[0]?.role || 'DEV';
  }

  isActive(c: Company): boolean {
    return this.tenant.active()?.id === c.id;
  }

  select(c: Company): void {
    this.tenant.setActive({
      id: c.id,
      name: c.name,
      role: this.roleOf(c),
    });
    Swal.fire({
      toast: true,
      position: 'top-end',
      icon: 'success',
      title: `Workspace "${c.name}" selecionado`,
      showConfirmButton: false,
      timer: 2500,
      timerProgressBar: true,
    });
  }

  async createCompany(): Promise<void> {
    const name = this.newName.trim();
    if (!name) {
      Swal.fire({
        icon: 'warning',
        title: 'Nome obrigatório',
        text: 'Informe o nome do workspace.',
      });
      return;
    }

    this.saving = true;
    try {
      const slug = this.newSlug.trim();
      const created = await this.api.createCompany(slug ? { name, slug } : { name });
      this.newName = '';
      this.newSlug = '';
      await this.loadCompanies();
      // Atualiza o seletor da navbar e já ativa o novo workspace.
      await this.workspaces.refresh();
      if (created?.id) {
        this.tenant.setActive({ id: created.id, name: created.name, role: 'OWNER' });
      }
      Swal.fire({
        icon: 'success',
        title: 'Workspace criado!',
        text: 'O workspace foi criado com sucesso.',
      });
    } catch (err) {
      console.error('Erro ao criar workspace: ', err);
      Swal.fire({
        icon: 'error',
        title: 'Erro ao criar workspace',
        text: 'Ocorreu um erro ao criar o workspace. Tente novamente.',
      });
    } finally {
      this.saving = false;
    }
  }
}
