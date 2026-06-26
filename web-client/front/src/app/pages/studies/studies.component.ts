import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import Swal from 'sweetalert2';

import { MaestroApiService } from '../../services/maestro-api.service';
import { StudyPlan, StudyCategory, StudyPlanStatus } from '../../models/maestro.models';

@Component({
  selector: 'app-studies',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './studies.component.html',
})
export class StudiesComponent implements OnInit {
  plans: StudyPlan[] = [];
  loading = false;

  // Filtros
  statusFilter = '';
  categoryFilter = '';

  // Criação
  showCreate = false;
  newPlan = { title: '', category: 'LINGUAGEM' as StudyCategory, description: '' };

  categories: StudyCategory[] = ['LINGUAGEM', 'FRAMEWORK', 'CERTIFICACAO', 'CONCEITO', 'CURSO', 'LIVRO'];
  statuses: StudyPlanStatus[] = ['PLANEJADO', 'EM_ANDAMENTO', 'PAUSADO', 'CONCLUIDO', 'ABANDONADO'];

  constructor(private api: MaestroApiService) {}

  ngOnInit(): void {
    this.load();
  }

  async load(): Promise<void> {
    this.loading = true;
    try {
      const filters: Record<string, string> = {};
      if (this.statusFilter) filters['status'] = this.statusFilter;
      if (this.categoryFilter) filters['category'] = this.categoryFilter;
      this.plans = await this.api.listStudyPlans(filters);
    } catch (err) {
      console.error('list study plans error', err);
    } finally {
      this.loading = false;
    }
  }

  async createPlan(): Promise<void> {
    const title = this.newPlan.title.trim();
    if (!title) return;
    try {
      await this.api.createStudyPlan({
        title,
        category: this.newPlan.category,
        description: this.newPlan.description || undefined,
      });
      this.showCreate = false;
      this.newPlan = { title: '', category: 'LINGUAGEM', description: '' };
      await this.load();
    } catch {
      Swal.fire({ icon: 'error', title: 'Erro', text: 'Não foi possível criar o plano.' });
    }
  }

  async deletePlan(id: number): Promise<void> {
    const result = await Swal.fire({
      icon: 'warning',
      title: 'Excluir plano?',
      text: 'Todos os tópicos e sessões serão removidos.',
      showCancelButton: true,
      confirmButtonText: 'Excluir',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#d33',
    });
    if (!result.isConfirmed) return;
    try {
      await this.api.deleteStudyPlan(id);
      await this.load();
    } catch {
      Swal.fire({ icon: 'error', title: 'Erro', text: 'Não foi possível excluir o plano.' });
    }
  }

  statusBadge(status: StudyPlanStatus): string {
    switch (status) {
      case 'EM_ANDAMENTO': return 'badge-primary';
      case 'CONCLUIDO': return 'badge-success';
      case 'PAUSADO': return 'badge-warning';
      case 'ABANDONADO': return 'badge-ghost';
      default: return 'badge-outline';
    }
  }

  statusLabel(status: StudyPlanStatus): string {
    switch (status) {
      case 'PLANEJADO': return 'Planejado';
      case 'EM_ANDAMENTO': return 'Em andamento';
      case 'PAUSADO': return 'Pausado';
      case 'CONCLUIDO': return 'Concluído';
      case 'ABANDONADO': return 'Abandonado';
    }
  }

  categoryLabel(cat: StudyCategory): string {
    switch (cat) {
      case 'LINGUAGEM': return 'Linguagem';
      case 'FRAMEWORK': return 'Framework';
      case 'CERTIFICACAO': return 'Certificação';
      case 'CONCEITO': return 'Conceito';
      case 'CURSO': return 'Curso';
      case 'LIVRO': return 'Livro';
    }
  }

  trackByPlan = (_: number, p: StudyPlan) => p.id;
}
