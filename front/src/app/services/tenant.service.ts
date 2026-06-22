import { Injectable, signal } from '@angular/core';

export interface ActiveCompany {
  id: number;
  name: string;
  role: string;
}

const KEY = 'maestro.company';

// Empresa ativa (multi-tenant). Persistida em localStorage; exposta como signal.
@Injectable({ providedIn: 'root' })
export class TenantService {
  private _active = signal<ActiveCompany | null>(this.read());
  readonly active = this._active.asReadonly();

  get companyId(): number | null {
    return this._active()?.id ?? null;
  }

  setActive(company: ActiveCompany): void {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(KEY, JSON.stringify(company));
    }
    this._active.set(company);
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
