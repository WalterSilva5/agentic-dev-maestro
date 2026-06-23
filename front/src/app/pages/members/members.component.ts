import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import Swal from 'sweetalert2';

import { MaestroApiService } from '../../services/maestro-api.service';
import { TenantService } from '../../services/tenant.service';
import { Member, Invitation } from '../../models/maestro.models';

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
  invitations: Invitation[] = [];
  loading = false;

  // form de convite
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
      const [members, invitations] = await Promise.all([
        this.api.listMembers(cid),
        this.api.listInvitations(cid).catch(() => [] as Invitation[]),
      ]);
      this.members = members;
      this.invitations = invitations;
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
      background: '#FFFFFF',
      color: '#111827',
      confirmButtonColor: '#1DB954',
      cancelButtonColor: '#6B7280',
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
        background: '#FFFFFF',
        color: '#111827',
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
      text: `${this.fullName(m)} (${m.user?.email}) perderá o acesso ao workspace.`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Remover',
      cancelButtonText: 'Cancelar',
      background: '#FFFFFF',
      color: '#111827',
      confirmButtonColor: '#F87272',
      cancelButtonColor: '#6B7280',
    });
    if (!confirm.isConfirmed) return;
    try {
      await this.api.removeMember(cid, m.id);
      await this.reload();
      Swal.fire({
        title: 'Membro removido',
        icon: 'success',
        background: '#FFFFFF',
        color: '#111827',
        confirmButtonColor: '#1DB954',
      });
    } catch (err: any) {
      this.fail(err, 'Falha ao remover membro');
    }
  }

  async invite(): Promise<void> {
    const cid = this.cid;
    if (cid == null) return;
    const email = this.newEmail.trim();
    if (!email) {
      Swal.fire({
        title: 'Informe um e-mail',
        icon: 'warning',
        background: '#FFFFFF',
        color: '#111827',
        confirmButtonColor: '#1DB954',
      });
      return;
    }
    this.adding = true;
    try {
      const res = await this.api.inviteMember(cid, { email, role: this.newRole });
      this.newEmail = '';
      this.newRole = 'DEV';
      await this.reload();
      Swal.fire({
        title: res.mode === 'added' ? 'Membro adicionado' : 'Convite enviado',
        text:
          res.mode === 'added'
            ? 'O usuário já tinha conta e agora faz parte do workspace.'
            : 'Enviamos um link de convite por e-mail. Ele aparece em "Convites pendentes".',
        icon: 'success',
        background: '#FFFFFF',
        color: '#111827',
        confirmButtonColor: '#1DB954',
      });
    } catch (err: any) {
      this.fail(err, 'Falha ao convidar');
    } finally {
      this.adding = false;
    }
  }

  async revokeInvite(inv: Invitation): Promise<void> {
    const cid = this.cid;
    if (cid == null) return;
    const confirm = await Swal.fire({
      title: 'Revogar convite?',
      text: `O convite para ${inv.email} deixará de ser válido.`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Revogar',
      cancelButtonText: 'Cancelar',
      background: '#FFFFFF',
      color: '#111827',
      confirmButtonColor: '#F87272',
      cancelButtonColor: '#6B7280',
    });
    if (!confirm.isConfirmed) return;
    try {
      await this.api.revokeInvitation(cid, inv.id);
      await this.reload();
    } catch (err: any) {
      this.fail(err, 'Falha ao revogar convite');
    }
  }

  private fail(err: any, fallback: string): void {
    const msg = err?.error?.messages ?? err?.error?.message ?? err?.message ?? fallback;
    Swal.fire({
      title: 'Erro',
      text: Array.isArray(msg) ? msg.join(', ') : String(msg),
      icon: 'error',
      background: '#FFFFFF',
      color: '#111827',
      confirmButtonColor: '#F87272',
    });
  }
}
