import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import Swal from 'sweetalert2';

import { MaestroApiService } from '../../services/maestro-api.service';
import { TenantService } from '../../services/tenant.service';
import { ApiKeyInfo } from '../../models/maestro.models';

const SCOPES = [
  'projects:read',
  'projects:write',
  'tasks:read',
  'tasks:write',
  'tasks:move',
  'docs:read',
  'docs:write',
] as const;

@Component({
  selector: 'app-api-keys',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './api-keys.component.html',
  styleUrl: './api-keys.component.scss',
})
export class ApiKeysComponent implements OnInit {
  readonly allScopes = SCOPES;

  keys: ApiKeyInfo[] = [];
  loading = false;

  // form de criação
  newLabel = '';
  selectedScopes: Record<string, boolean> = {};
  creating = false;

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
      this.keys = await this.api.listApiKeys(cid);
    } catch (err: any) {
      this.fail(err, 'Falha ao carregar chaves');
    } finally {
      this.loading = false;
    }
  }

  private pickedScopes(): string[] {
    return this.allScopes.filter((s) => this.selectedScopes[s]);
  }

  async create(): Promise<void> {
    const cid = this.cid;
    if (cid == null) return;
    const label = this.newLabel.trim();
    if (!label) {
      Swal.fire({
        title: 'Informe um rótulo',
        icon: 'warning',
        background: '#1E1E1E',
        color: '#FFFFFF',
        confirmButtonColor: '#1DB954',
      });
      return;
    }
    this.creating = true;
    try {
      const scopes = this.pickedScopes();
      const created = await this.api.createApiKey(cid, {
        label,
        scopes: scopes.length ? scopes : undefined,
      });
      this.newLabel = '';
      this.selectedScopes = {};
      await this.reload();
      if (created?.secret) {
        await this.showSecret(created);
      } else {
        Swal.fire({
          title: 'Chave criada',
          icon: 'success',
          background: '#1E1E1E',
          color: '#FFFFFF',
          confirmButtonColor: '#1DB954',
        });
      }
    } catch (err: any) {
      this.fail(err, 'Falha ao criar chave');
    } finally {
      this.creating = false;
    }
  }

  private async showSecret(key: ApiKeyInfo): Promise<void> {
    const secret = key.secret ?? '';
    const esc = (s: string) =>
      s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    await Swal.fire({
      title: 'Chave criada',
      icon: 'success',
      width: 600,
      background: '#1E1E1E',
      color: '#FFFFFF',
      confirmButtonText: 'Copiar e fechar',
      confirmButtonColor: '#1DB954',
      html: `
        <p style="margin:0 0 .75rem; color:#D0D0D0; text-align:left;">
          Rótulo: <strong>${esc(key.label)}</strong>
        </p>
        <div style="background:#FBBD23; color:#121212; padding:.5rem .75rem; border-radius:8px;
                    font-weight:600; text-align:left; margin-bottom:.75rem;">
          Copie agora, não será exibido novamente.
        </div>
        <textarea readonly id="maestro-secret"
          style="width:100%; min-height:72px; background:#121212; color:#1DB954; border:1px solid #2A2A2A;
                 border-radius:8px; padding:.6rem; font-family:monospace; font-size:.85rem; resize:none;"
          onclick="this.select()">${esc(secret)}</textarea>
      `,
      didOpen: () => {
        const ta = document.getElementById('maestro-secret') as HTMLTextAreaElement | null;
        ta?.select();
      },
      preConfirm: async () => {
        try {
          await navigator.clipboard.writeText(secret);
        } catch {
          /* clipboard pode falhar sem HTTPS; o usuário ainda pode copiar manualmente */
        }
      },
    });
  }

  async revoke(key: ApiKeyInfo): Promise<void> {
    const cid = this.cid;
    if (cid == null) return;
    const confirm = await Swal.fire({
      title: 'Revogar chave?',
      text: `A chave "${key.label}" (${key.prefix}…) deixará de funcionar imediatamente.`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Revogar',
      cancelButtonText: 'Cancelar',
      background: '#1E1E1E',
      color: '#FFFFFF',
      confirmButtonColor: '#F87272',
      cancelButtonColor: '#2A2A2A',
    });
    if (!confirm.isConfirmed) return;
    try {
      await this.api.revokeApiKey(cid, key.id);
      await this.reload();
      Swal.fire({
        title: 'Chave revogada',
        icon: 'success',
        background: '#1E1E1E',
        color: '#FFFFFF',
        confirmButtonColor: '#1DB954',
      });
    } catch (err: any) {
      this.fail(err, 'Falha ao revogar chave');
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
