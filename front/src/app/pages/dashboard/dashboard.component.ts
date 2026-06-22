import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

import { MaestroApiService } from '../../services/maestro-api.service';
import { TenantService } from '../../services/tenant.service';
import { Project, ActivityItem } from '../../models/maestro.models';

// Resumo por coluna do quadro de um projeto.
interface ColumnStat {
  name: string;
  count: number;
  isDone: boolean;
}

// View model de progresso por projeto.
interface ProjectProgress {
  id: number;
  name: string;
  key: string;
  total: number;
  done: number;
  percent: number;
  columns: ColumnStat[];
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss'],
})
export class DashboardComponent implements OnInit {
  loading = false;

  progress: ProjectProgress[] = [];
  activity: ActivityItem[] = [];

  constructor(
    private api: MaestroApiService,
    protected tenant: TenantService
  ) {}

  get hasCompany(): boolean {
    return this.tenant.companyId !== null;
  }

  // Totais agregados para a faixa de estatísticas do topo.
  get totalProjects(): number {
    return this.progress.length;
  }

  get totalTasks(): number {
    return this.progress.reduce((acc, p) => acc + p.total, 0);
  }

  get totalDone(): number {
    return this.progress.reduce((acc, p) => acc + p.done, 0);
  }

  get aggregatePercent(): number {
    return this.pct(this.totalDone, this.totalTasks);
  }

  async ngOnInit(): Promise<void> {
    if (this.tenant.companyId === null) return;
    await this.load();
  }

  async load(): Promise<void> {
    this.loading = true;
    try {
      const projects = await this.api.listProjects();

      // Carrega os quadros em paralelo e monta o view model de progresso.
      this.progress = await Promise.all(
        projects.map((p) => this.buildProgress(p))
      );

      this.activity = await this.api.listActivity({ limit: 10 });
    } catch (err) {
      console.error('Erro ao carregar o dashboard: ', err);
    } finally {
      this.loading = false;
    }
  }

  private async buildProgress(p: Project): Promise<ProjectProgress> {
    const board = await this.api.getBoard(p.id);
    const columns = board?.columns ?? [];

    const columnStats: ColumnStat[] = columns.map((c) => ({
      name: c.name,
      count: c.tasks?.length ?? 0,
      isDone: c.isDone,
    }));

    const total = columnStats.reduce((acc, c) => acc + c.count, 0);
    const done = columnStats
      .filter((c) => c.isDone)
      .reduce((acc, c) => acc + c.count, 0);

    return {
      id: p.id,
      name: p.name,
      key: p.key,
      total,
      done,
      percent: this.pct(done, total),
      columns: columnStats,
    };
  }

  private pct(done: number, total: number): number {
    if (!total) return 0;
    return Math.round((done / total) * 100);
  }
}
