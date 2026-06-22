import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import Swal from 'sweetalert2';

import { MaestroApiService } from '../../services/maestro-api.service';
import { TenantService } from '../../services/tenant.service';
import { Member } from '../../models/maestro.models';

const ROLES = ['OWNER', 'MANAGER', 'TECH_LEAD', 'DEV', 'VIEWER'] as const;

@Component({
  selector: 'app-members',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './members.component.html',
  styleUrl: './members.component.scss',
})
export class MembersComponent implements OnInit {
  readonly roles = ROLES;

  members: Member[] = [];
  loading = false;

  // form de adição
  newEmail = '';
  newRole = 'DEV';
  adding = false;

  constructor(private api: MaestroApiService, protected tenant: TenantService) {}

  get cid(): number | null {
    return this.tenant.companyId;
  }

  ngOnInit(): void {
    if (this.cid != null) this.reload();
  }

  async reload(): Promise<void> {
    const cid = this.cid;
    if (cid == null) return;
    this.loading = true;
    try {
      this.members = await this.api.listMembers(cid);
    } catch (err: any) {
      this.fail(err, 'Falha ao carregar membros');
    } finally {
      this.loading = false;
    }
  }

  fullName(m: Member): string {
    return `${m.user?.firstName ?? ''} ${m.user?.lastName ?? ''}`.trim() || '-';
  }

  async onRoleChange(m: Member, newRole: string): Promise<void> {
    const cid = this.cid;
    if (cid == null) return;
    const previous = m.role;
    const confirm = await Swal.fire({
      title: 'Alterar papel?',
      text: `Definir ${this.fullName(m)} como ${newRole}?`,
      icon: 'question',
      showCancelButton: true,
      confirmButtonText: 'Confirmar',
      cancelButtonText: 'Cancelar',
      background: '#1E1E1E',
      color: '#FFFFFF',
      confirmButtonColor: '#1DB954',
      cancelButtonColor: '#2A2A2A',
    });
    if (!confirm.isConfirmed) {
      m.role = previous; // reverte o select
      return;
    }
    try {
      await this.api.updateMemberRole(cid, m.id, newRole);
      m.role = newRole;
      Swal.fire({
        title: 'Papel atualizado',
        icon: 'success',
        background: '#1E1E1E',
        color: '#FFFFFF',
        confirmButtonColor: '#1DB954',
      });
    } catch (err: any) {
      m.role = previous; // reverte
      this.fail(err, 'Falha ao atualizar papel');
    }
  }

  async remove(m: Member): Promise<void> {
    const cid = this.cid;
    if (cid == null) return;
    const confirm = await Swal.fire({
      title: 'Remover membro?',
      text: `${this.fullName(m)} (${m.user?.email}) perderá o acesso à empresa.`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Remover',
      cancelButtonText: 'Cancelar',
      background: '#1E1E1E',
      color: '#FFFFFF',
      confirmButtonColor: '#F87272',
      cancelButtonColor: '#2A2A2A',
    });
    if (!confirm.isConfirmed) return;
    try {
      await this.api.removeMember(cid, m.id);
      await this.reload();
      Swal.fire({
        title: 'Membro removido',
        icon: 'success',
        background: '#1E1E1E',
        color: '#FFFFFF',
        confirmButtonColor: '#1DB954',
      });
    } catch (err: any) {
      this.fail(err, 'Falha ao remover membro');
    }
  }

  async add(): Promise<void> {
    const cid = this.cid;
    if (cid == null) return;
    const email = this.newEmail.trim();
    if (!email) {
      Swal.fire({
        title: 'Informe um e-mail',
        icon: 'warning',
        background: '#1E1E1E',
        color: '#FFFFFF',
        confirmButtonColor: '#1DB954',
      });
      return;
    }
    this.adding = true;
    try {
      await this.api.addMember(cid, { email, role: this.newRole });
      this.newEmail = '';
      this.newRole = 'DEV';
      await this.reload();
      Swal.fire({
        title: 'Membro adicionado',
        icon: 'success',
        background: '#1E1E1E',
        color: '#FFFFFF',
        confirmButtonColor: '#1DB954',
      });
    } catch (err: any) {
      this.fail(err, 'Falha ao adicionar membro');
    } finally {
      this.adding = false;
    }
  }

  private fail(err: any, fallback: string): void {
    const msg = err?.error?.messages ?? err?.error?.message ?? err?.message ?? fallback;
    Swal.fire({
      title: 'Erro',
      text: Array.isArray(msg) ? msg.join(', ') : String(msg),
      icon: 'error',
      background: '#1E1E1E',
      color: '#FFFFFF',
      confirmButtonColor: '#F87272',
    });
  }
}
