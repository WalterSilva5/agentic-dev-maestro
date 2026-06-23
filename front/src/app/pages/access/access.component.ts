import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import Swal from 'sweetalert2';

import { MaestroApiService } from '../../services/maestro-api.service';
import { TenantService } from '../../services/tenant.service';
import { Member } from '../../models/maestro.models';

const ROLES = ['OWNER', 'MANAGER', 'TECH_LEAD', 'DEV', 'VIEWER'] as const;

const ROLE_LABELS: Record<string, string> = {
  OWNER: 'Proprietário',
  MANAGER: 'Gerente',
  TECH_LEAD: 'Tech Lead',
  DEV: 'Desenvolvedor',
  VIEWER: 'Visualizador',
};

interface PermissionRow {
  action: string;
  description: string;
  roles: string[];
}

const PERMISSIONS_MATRIX: PermissionRow[] = [
  { action: 'Ver dashboard', description: 'Acessar o dashboard do workspace', roles: ['OWNER', 'MANAGER', 'TECH_LEAD', 'DEV', 'VIEWER'] },
  { action: 'Ver projetos e board', description: 'Visualizar projetos, quadros e tarefas', roles: ['OWNER', 'MANAGER', 'TECH_LEAD', 'DEV', 'VIEWER'] },
  { action: 'Criar tarefas', description: 'Criar novas tarefas nos projetos', roles: ['OWNER', 'MANAGER', 'TECH_LEAD', 'DEV'] },
  { action: 'Editar tarefas', description: 'Alterar título, descrição, prioridade, etc.', roles: ['OWNER', 'MANAGER', 'TECH_LEAD', 'DEV'] },
  { action: 'Mover tarefas', description: 'Arrastar cards entre colunas do board', roles: ['OWNER', 'MANAGER', 'TECH_LEAD', 'DEV'] },
  { action: 'Comentar', description: 'Adicionar comentários às tarefas', roles: ['OWNER', 'MANAGER', 'TECH_LEAD', 'DEV'] },
  { action: 'Criar projetos', description: 'Criar novos projetos no workspace', roles: ['OWNER', 'MANAGER', 'TECH_LEAD'] },
  { action: 'Gerenciar labels', description: 'Criar e excluir labels do workspace', roles: ['OWNER', 'MANAGER', 'TECH_LEAD'] },
  { action: 'Gerenciar documentos', description: 'Criar, editar e excluir documentos', roles: ['OWNER', 'MANAGER', 'TECH_LEAD', 'DEV'] },
  { action: 'Convidar membros', description: 'Enviar convites para novos membros', roles: ['OWNER', 'MANAGER'] },
  { action: 'Alterar papéis', description: 'Mudar o papel de membros da equipe', roles: ['OWNER', 'MANAGER'] },
  { action: 'Remover membros', description: 'Remover membros do workspace', roles: ['OWNER', 'MANAGER'] },
  { action: 'Gerenciar API keys', description: 'Criar e revogar chaves de API', roles: ['OWNER', 'MANAGER'] },
  { action: 'Gerenciar webhooks', description: 'Configurar webhooks de integração', roles: ['OWNER', 'MANAGER'] },
  { action: 'Excluir workspace', description: 'Excluir permanentemente o workspace', roles: ['OWNER'] },
];

@Component({
  selector: 'app-access',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './access.component.html',
  styleUrl: './access.component.scss',
})
export class AccessComponent implements OnInit {
  readonly roles = ROLES;
  readonly roleLabels = ROLE_LABELS;
  readonly matrix = PERMISSIONS_MATRIX;

  members: Member[] = [];
  loading = false;

  constructor(
    private api: MaestroApiService,
    protected tenant: TenantService,
  ) {}

  get hasCompany(): boolean {
    return this.tenant.companyId != null;
  }

  ngOnInit(): void {
    if (this.hasCompany) this.loadMembers();
  }

  async loadMembers(): Promise<void> {
    const cid = this.tenant.companyId;
    if (cid == null) return;
    this.loading = true;
    try {
      this.members = await this.api.listMembers(cid);
    } catch {
      console.error('Erro ao carregar membros');
    } finally {
      this.loading = false;
    }
  }

  hasPermission(row: PermissionRow, role: string): boolean {
    return row.roles.includes(role);
  }

  fullName(m: Member): string {
    return `${m.user?.firstName ?? ''} ${m.user?.lastName ?? ''}`.trim() || '-';
  }

  async onRoleChange(m: Member, newRole: string): Promise<void> {
    const cid = this.tenant.companyId;
    if (cid == null) return;
    const previous = m.role;
    const confirm = await Swal.fire({
      title: 'Alterar papel?',
      text: `Definir ${this.fullName(m)} como ${this.roleLabels[newRole] || newRole}?`,
      icon: 'question',
      showCancelButton: true,
      confirmButtonText: 'Confirmar',
      cancelButtonText: 'Cancelar',
      background: '#FFFFFF',
      color: '#111827',
      confirmButtonColor: '#1DB954',
      cancelButtonColor: '#6B7280',
    });
    if (!confirm.isConfirmed) {
      m.role = previous;
      return;
    }
    try {
      await this.api.updateMemberRole(cid, m.id, newRole);
      m.role = newRole;
      Swal.fire({ title: 'Papel atualizado', icon: 'success', timer: 1500, showConfirmButton: false });
    } catch {
      m.role = previous;
      Swal.fire({ icon: 'error', title: 'Erro', text: 'Não foi possível alterar o papel.' });
    }
  }
}
