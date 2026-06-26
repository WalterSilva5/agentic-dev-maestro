import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { Store } from '@ngrx/store';
import { take } from 'rxjs/operators';
import Swal from 'sweetalert2';

import { MaestroApiService } from '../../services/maestro-api.service';
import { WorkspaceService } from '../../services/workspace.service';
import { TenantService } from '../../services/tenant.service';
import { selectAuthState } from '../../state/auth/auth.selectors';
import { InvitationDetails } from '../../models/maestro.models';

// Página de aceite de convite (link enviado por e-mail). Pública: mostra os
// detalhes; se o usuário não estiver logado, leva ao login/cadastro e volta.
@Component({
  selector: 'app-invite',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './invite.component.html',
  styleUrls: ['./invite.component.scss'],
})
export class InviteComponent implements OnInit {
  token = '';
  loading = signal(true);
  accepting = signal(false);
  details = signal<InvitationDetails | null>(null);
  error = signal<string | null>(null);
  isAuthenticated = false;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private api: MaestroApiService,
    private workspaces: WorkspaceService,
    private tenant: TenantService,
    private store: Store
  ) {}

  async ngOnInit(): Promise<void> {
    this.token = this.route.snapshot.paramMap.get('token') ?? '';
    this.store
      .select(selectAuthState)
      .pipe(take(1))
      .subscribe((a) => (this.isAuthenticated = a.isAuthenticated));

    try {
      this.details.set(await this.api.getInvitation(this.token));
    } catch {
      this.error.set('Convite inválido, expirado ou já utilizado.');
    } finally {
      this.loading.set(false);
    }
  }

  private rememberAndGo(path: string): void {
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('returnUrl', `/invite/${this.token}`);
    }
    this.router.navigate([path]);
  }

  goLogin(): void {
    this.rememberAndGo('/auth/login');
  }

  goRegister(): void {
    this.rememberAndGo('/auth/register');
  }

  async accept(): Promise<void> {
    this.accepting.set(true);
    try {
      const res = await this.api.acceptInvitation(this.token);
      const list = await this.workspaces.refresh();
      const ws = list.find((w) => w.id === res.companyId);
      if (ws) this.tenant.setActive(ws);
      await Swal.fire({
        icon: 'success',
        title: res.alreadyMember ? 'Você já fazia parte!' : 'Convite aceito!',
        text: 'Workspace ativado.',
        timer: 1800,
        showConfirmButton: false,
      });
      this.router.navigate(['/projects']);
    } catch (e: unknown) {
      const msg =
        (e as { error?: { messages?: string[] } })?.error?.messages?.[0] ??
        'Não foi possível aceitar o convite.';
      Swal.fire({ icon: 'error', title: 'Erro', text: msg });
    } finally {
      this.accepting.set(false);
    }
  }
}
