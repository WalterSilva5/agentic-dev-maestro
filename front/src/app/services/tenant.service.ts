import { Injectable, computed, signal } from '@angular/core';

export interface ActiveCompany {
  id: number;
  name: string;
  role: string;
}

const KEY = 'maestro.company';

// Workspace ativo (multi-tenant) + lista de workspaces do usuário.
// O ativo é persistido em localStorage; ambos expostos como signals.
@Injectable({ providedIn: 'root' })
export class TenantService {
  private _active = signal<ActiveCompany | null>(this.read());
  readonly active = this._active.asReadonly();

  private _workspaces = signal<ActiveCompany[]>([]);
  readonly workspaces = this._workspaces.asReadonly();

  readonly hasWorkspaces = computed(() => this._workspaces().length > 0);

  get companyId(): number | null {
    return this._active()?.id ?? null;
  }

  setActive(company: ActiveCompany): void {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(KEY, JSON.stringify(company));
    }
    this._active.set(company);
  }

  // Define a lista de workspaces e garante que o ativo seja um deles
  // (se o ativo sumiu ou nunca foi escolhido, seleciona o primeiro).
  setWorkspaces(list: ActiveCompany[]): void {
    this._workspaces.set(list);
    const active = this._active();
    if (!list.length) {
      this.clear();
      return;
    }
    if (!active || !list.some((w) => w.id === active.id)) {
      this.setActive(list[0]);
    } else {
      const fresh = list.find((w) => w.id === active.id);
      if (fresh && fresh.role !== active.role) this.setActive(fresh);
    }
  }

  clear(): void {
    if (typeof window !== 'undefined') window.localStorage.removeItem(KEY);
    this._active.set(null);
  }

  private read(): ActiveCompany | null {
    if (typeof window === 'undefined') return null;
    try {
      const raw = window.localStorage.getItem(KEY);
      return raw ? (JSON.parse(raw) as ActiveCompany) : null;
    } catch {
      return null;
    }
  }
}
