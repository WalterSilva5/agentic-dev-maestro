import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import Swal from 'sweetalert2';

import { MaestroApiService } from '../../services/maestro-api.service';
import { TenantService } from '../../services/tenant.service';
import { Label } from '../../models/maestro.models';

const COLOR_PALETTE = [
  { name: 'Vermelho', value: '#EF4444' },
  { name: 'Laranja', value: '#F97316' },
  { name: 'Âmbar', value: '#F59E0B' },
  { name: 'Verde', value: '#22C55E' },
  { name: 'Esmeralda', value: '#10B981' },
  { name: 'Ciano', value: '#06B6D4' },
  { name: 'Azul', value: '#3B82F6' },
  { name: 'Índigo', value: '#6366F1' },
  { name: 'Violeta', value: '#8B5CF6' },
  { name: 'Rosa', value: '#EC4899' },
  { name: 'Cinza', value: '#6B7280' },
  { name: 'Ardósia', value: '#475569' },
];

@Component({
  selector: 'app-labels',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './labels.component.html',
  styleUrl: './labels.component.scss',
})
export class LabelsComponent implements OnInit {
  readonly palette = COLOR_PALETTE;

  labels: Label[] = [];
  loading = false;

  newName = '';
  newColor = COLOR_PALETTE[6].value;
  saving = false;

  constructor(
    private api: MaestroApiService,
    protected tenant: TenantService,
  ) {}

  get hasCompany(): boolean {
    return this.tenant.companyId != null;
  }

  ngOnInit(): void {
    if (this.hasCompany) this.reload();
  }

  async reload(): Promise<void> {
    this.loading = true;
    try {
      this.labels = await this.api.listLabels();
    } catch {
      Swal.fire({ icon: 'error', title: 'Erro', text: 'Não foi possível carregar as labels.' });
    } finally {
      this.loading = false;
    }
  }

  async create(): Promise<void> {
    const name = this.newName.trim();
    if (!name) {
      Swal.fire({ icon: 'warning', title: 'Nome obrigatório', text: 'Informe o nome da label.' });
      return;
    }
    this.saving = true;
    try {
      await this.api.createLabel({ name, color: this.newColor });
      this.newName = '';
      this.newColor = COLOR_PALETTE[6].value;
      await this.reload();
      Swal.fire({ icon: 'success', title: 'Label criada!', timer: 1500, showConfirmButton: false });
    } catch (err: any) {
      const msg = err?.error?.message ?? 'Não foi possível criar a label.';
      Swal.fire({ icon: 'error', title: 'Erro', text: msg });
    } finally {
      this.saving = false;
    }
  }

  async remove(label: Label): Promise<void> {
    const confirm = await Swal.fire({
      title: 'Excluir label?',
      text: `A label "${label.name}" será removida de todas as tarefas.`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Excluir',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#F87272',
      cancelButtonColor: '#6B7280',
    });
    if (!confirm.isConfirmed) return;
    try {
      await this.api.deleteLabel(label.id);
      await this.reload();
    } catch {
      Swal.fire({ icon: 'error', title: 'Erro', text: 'Não foi possível excluir a label.' });
    }
  }

  selectColor(color: string): void {
    this.newColor = color;
  }
}
