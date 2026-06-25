import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MaestroApiService } from '../../services/maestro-api.service';
import { MetricsResponse } from '../../models/maestro.models';

const TYPE_LABELS: Record<string, string> = {
  FEATURE: 'Feature',
  BUG: 'Bug',
  TECH_DEBT: 'Dívida Técnica',
  IMPROVEMENT: 'Melhoria',
  CHORE: 'Tarefa'
};

const PRIORITY_LABELS: Record<string, string> = {
  LOW: 'Baixa',
  MEDIUM: 'Média',
  HIGH: 'Alta',
  URGENT: 'Urgente'
};

const PRIORITY_COLORS: Record<string, string> = {
  LOW: '#6B7280',
  MEDIUM: '#3B82F6',
  HIGH: '#F59E0B',
  URGENT: '#EF4444'
};

const TYPE_COLORS: Record<string, string> = {
  FEATURE: '#8B5CF6',
  BUG: '#EF4444',
  TECH_DEBT: '#F59E0B',
  IMPROVEMENT: '#10B981',
  CHORE: '#6B7280'
};

@Component({
  selector: 'app-metrics',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './metrics.component.html',
  styleUrls: ['./metrics.component.scss']
})
export class MetricsComponent implements OnInit {
  loading = true;
  metrics: MetricsResponse | null = null;

  typeLabels = TYPE_LABELS;
  priorityLabels = PRIORITY_LABELS;
  priorityColors = PRIORITY_COLORS;
  typeColors = TYPE_COLORS;

  constructor(private api: MaestroApiService) {}

  ngOnInit() {
    this.load();
  }

  async load() {
    this.loading = true;
    try {
      this.metrics = await this.api.getMetrics();
    } catch (err) {
      console.error('Failed to load metrics', err);
    } finally {
      this.loading = false;
    }
  }

  formatHours(hours: number | null): string {
    if (hours === null) return '—';
    if (hours < 1) return `${Math.round(hours * 60)} min`;
    if (hours < 24) return `${Math.round(hours * 10) / 10} h`;
    const days = Math.round((hours / 24) * 10) / 10;
    return `${days} dias`;
  }

  typeEntries(): { key: string; label: string; color: string; total: number; done: number; percent: number }[] {
    if (!this.metrics) return [];
    return Object.entries(this.metrics.byType).map(([key, v]) => ({
      key,
      label: TYPE_LABELS[key] || key,
      color: TYPE_COLORS[key] || '#6B7280',
      total: v.total,
      done: v.done,
      percent: v.total ? Math.round((v.done / v.total) * 100) : 0
    }));
  }

  priorityEntries(): { key: string; label: string; color: string; total: number; done: number; percent: number }[] {
    if (!this.metrics) return [];
    return Object.entries(this.metrics.byPriority).map(([key, v]) => ({
      key,
      label: PRIORITY_LABELS[key] || key,
      color: PRIORITY_COLORS[key] || '#6B7280',
      total: v.total,
      done: v.done,
      percent: v.total ? Math.round((v.done / v.total) * 100) : 0
    }));
  }

  maxThroughput(): number {
    if (!this.metrics) return 1;
    return Math.max(1, ...this.metrics.weeklyThroughput.map(w => w.count));
  }
}
