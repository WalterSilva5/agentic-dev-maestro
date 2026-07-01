import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import Swal from 'sweetalert2';

import { MaestroApiService } from '../../../services/maestro-api.service';
import { StudyPlan, StudyTopic, StudyTopicStatus, StudyPlanStatus, StudyCategory } from '../../../models/maestro.models';

@Component({
  selector: 'app-study-plan',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './study-plan.component.html',
})
export class StudyPlanComponent implements OnInit, OnDestroy {
  plan: StudyPlan | null = null;
  topics: StudyTopic[] = [];
  loading = true;
  planId!: number;

  // Adicionar topico
  showAddTopic = false;
  newTopic = { title: '', description: '', estimateHours: null as number | null, parentId: null as number | null };

  // Edicao do plano
  editingPlan = false;
  editPlanData = { title: '', description: '', status: '' as string, targetDate: '' };

  // Sessao ativa
  activeSession: { topicId: number; startedAt: Date; topicTitle: string } | null = null;
  sessionElapsed = '';
  sessionTimer: any = null;

  // UI state
  expandedTopics: Set<number> = new Set();
  showNotes: number | null = null;
  editingNotes = '';

  statuses: StudyPlanStatus[] = ['PLANEJADO', 'EM_ANDAMENTO', 'PAUSADO', 'CONCLUIDO', 'ABANDONADO'];

  constructor(
    private api: MaestroApiService,
    private route: ActivatedRoute,
    private router: Router,
  ) {}

  ngOnInit(): void {
    this.planId = Number(this.route.snapshot.paramMap.get('id'));
    this.load();
  }

  ngOnDestroy(): void {
    if (this.sessionTimer) {
      clearInterval(this.sessionTimer);
    }
  }

  async load(): Promise<void> {
    this.loading = true;
    try {
      const [plan, topics] = await Promise.all([
        this.api.getStudyPlan(this.planId),
        this.api.listStudyTopics(this.planId),
      ]);
      this.plan = plan;
      this.topics = topics;
    } catch (err) {
      console.error('load study plan error', err);
    } finally {
      this.loading = false;
    }
  }

  // ---- Topicos ----

  async addTopic(): Promise<void> {
    const title = this.newTopic.title.trim();
    if (!title) return;
    try {
      await this.api.createStudyTopic(this.planId, {
        title,
        description: this.newTopic.description || undefined,
        estimateHours: this.newTopic.estimateHours ?? undefined,
        parentId: this.newTopic.parentId ?? undefined,
      });
      this.showAddTopic = false;
      this.newTopic = { title: '', description: '', estimateHours: null, parentId: null };
      await this.load();
    } catch {
      Swal.fire({ icon: 'error', title: 'Erro', text: 'Nao foi possivel adicionar o topico.' });
    }
  }

  async deleteTopic(id: number): Promise<void> {
    const result = await Swal.fire({
      icon: 'warning',
      title: 'Excluir topico?',
      text: 'As sessoes vinculadas tambem serao removidas.',
      showCancelButton: true,
      confirmButtonText: 'Excluir',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#d33',
    });
    if (!result.isConfirmed) return;
    try {
      await this.api.deleteStudyTopic(id);
      await this.load();
    } catch {
      Swal.fire({ icon: 'error', title: 'Erro', text: 'Nao foi possivel excluir o topico.' });
    }
  }

  async updateTopicStatus(topic: StudyTopic, newStatus: StudyTopicStatus): Promise<void> {
    try {
      await this.api.updateStudyTopic(topic.id, { status: newStatus });
      topic.status = newStatus;
      await this.load();
    } catch {
      Swal.fire({ icon: 'error', title: 'Erro', text: 'Nao foi possivel atualizar o status.' });
    }
  }

  // ---- Plano ----

  openEditPlan(): void {
    if (!this.plan) return;
    this.editPlanData = {
      title: this.plan.title,
      description: this.plan.description || '',
      status: this.plan.status,
      targetDate: this.plan.targetDate || '',
    };
    this.editingPlan = true;
  }

  async updatePlan(): Promise<void> {
    try {
      await this.api.updateStudyPlan(this.planId, {
        title: this.editPlanData.title,
        description: this.editPlanData.description || undefined,
        status: this.editPlanData.status as StudyPlanStatus,
        targetDate: this.editPlanData.targetDate || undefined,
      });
      this.editingPlan = false;
      await this.load();
    } catch {
      Swal.fire({ icon: 'error', title: 'Erro', text: 'Nao foi possivel atualizar o plano.' });
    }
  }

  async deletePlan(): Promise<void> {
    const result = await Swal.fire({
      icon: 'warning',
      title: 'Excluir plano?',
      text: 'Todos os topicos e sessoes serao removidos.',
      showCancelButton: true,
      confirmButtonText: 'Excluir',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#d33',
    });
    if (!result.isConfirmed) return;
    try {
      await this.api.deleteStudyPlan(this.planId);
      this.router.navigate(['/studies']);
    } catch {
      Swal.fire({ icon: 'error', title: 'Erro', text: 'Nao foi possivel excluir o plano.' });
    }
  }

  // ---- Sessao de estudo ----

  startSession(topic: StudyTopic): void {
    this.activeSession = {
      topicId: topic.id,
      startedAt: new Date(),
      topicTitle: topic.title,
    };
    this.sessionElapsed = '00:00:00';
    this.sessionTimer = setInterval(() => this.updateTimer(), 1000);
  }

  async stopSession(): Promise<void> {
    if (!this.activeSession) return;
    clearInterval(this.sessionTimer);
    this.sessionTimer = null;

    const elapsed = Date.now() - this.activeSession.startedAt.getTime();
    const durationMin = Math.round(elapsed / 60000);

    try {
      await this.api.createStudySession({
        topicId: this.activeSession.topicId,
        startedAt: this.activeSession.startedAt.toISOString(),
        endedAt: new Date().toISOString(),
        durationMin: Math.max(durationMin, 1),
      });
      this.activeSession = null;
      this.sessionElapsed = '';
      await this.load();
    } catch {
      Swal.fire({ icon: 'error', title: 'Erro', text: 'Nao foi possivel registrar a sessao.' });
    }
  }

  private updateTimer(): void {
    if (!this.activeSession) return;
    const elapsed = Date.now() - this.activeSession.startedAt.getTime();
    const h = Math.floor(elapsed / 3600000);
    const m = Math.floor((elapsed % 3600000) / 60000);
    const s = Math.floor((elapsed % 60000) / 1000);
    this.sessionElapsed = `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  }

  // ---- Notas ----

  toggleNotes(topicId: number): void {
    if (this.showNotes === topicId) {
      this.showNotes = null;
    } else {
      this.showNotes = topicId;
      const topic = this.topics.find(t => t.id === topicId);
      this.editingNotes = topic?.notes || '';
    }
  }

  async saveNotes(topicId: number): Promise<void> {
    try {
      await this.api.updateStudyTopic(topicId, { notes: this.editingNotes });
      this.showNotes = null;
      await this.load();
    } catch {
      Swal.fire({ icon: 'error', title: 'Erro', text: 'Nao foi possivel salvar as notas.' });
    }
  }

  // ---- Expand/collapse ----

  toggleExpand(topicId: number): void {
    if (this.expandedTopics.has(topicId)) {
      this.expandedTopics.delete(topicId);
    } else {
      this.expandedTopics.add(topicId);
    }
  }

  // ---- Helpers ----

  formatDuration(minutes: number): string {
    if (!minutes) return '0m';
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    if (h > 0 && m > 0) return `${h}h ${m}m`;
    if (h > 0) return `${h}h`;
    return `${m}m`;
  }

  topicStatusColor(status: StudyTopicStatus): { bg: string; text: string; border: string; surface: string } {
    switch (status) {
      case 'PENDENTE':
        return { bg: '#9CA3AF', text: '#6B7280', border: '#D1D5DB', surface: 'rgb(243 244 246)' };
      case 'ESTUDANDO':
        return { bg: '#3B82F6', text: '#2563EB', border: '#93C5FD', surface: 'rgb(239 246 255)' };
      case 'REVISAO':
        return { bg: '#F59E0B', text: '#D97706', border: '#FCD34D', surface: 'rgb(255 251 235)' };
      case 'CONCLUIDO':
        return { bg: '#1DB954', text: '#16a34a', border: '#86EFAC', surface: 'rgb(240 253 244)' };
      case 'PULADO':
        return { bg: '#64748B', text: '#475569', border: '#CBD5E1', surface: 'rgb(241 245 249)' };
    }
  }

  topicStatusLabel(status: StudyTopicStatus): string {
    switch (status) {
      case 'PENDENTE': return 'Pendente';
      case 'ESTUDANDO': return 'Estudando';
      case 'REVISAO': return 'Revisao';
      case 'CONCLUIDO': return 'Concluido';
      case 'PULADO': return 'Pulado';
    }
  }

  topicStatusIcon(status: StudyTopicStatus): string {
    switch (status) {
      case 'PENDENTE': return '○';
      case 'ESTUDANDO': return '▶';
      case 'REVISAO': return '↻';
      case 'CONCLUIDO': return '✓';
      case 'PULADO': return '⊘';
    }
  }

  confidenceStars(confidence: number | undefined): boolean[] {
    const level = confidence ?? 0;
    return [1, 2, 3, 4, 5].map(i => i <= level);
  }

  async setConfidence(topicId: number, confidence: number): Promise<void> {
    try {
      await this.api.createStudySession({
        topicId,
        startedAt: new Date().toISOString(),
        confidence,
        durationMin: 0,
      });
      await this.load();
    } catch {
      Swal.fire({ icon: 'error', title: 'Erro', text: 'Nao foi possivel registrar a confianca.' });
    }
  }

  statusLabel(status: StudyPlanStatus): string {
    switch (status) {
      case 'PLANEJADO': return 'Planejado';
      case 'EM_ANDAMENTO': return 'Em andamento';
      case 'PAUSADO': return 'Pausado';
      case 'CONCLUIDO': return 'Concluido';
      case 'ABANDONADO': return 'Abandonado';
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

  categoryLabel(cat: StudyCategory): string {
    switch (cat) {
      case 'LINGUAGEM': return 'Linguagem';
      case 'FRAMEWORK': return 'Framework';
      case 'CERTIFICACAO': return 'Certificacao';
      case 'CONCEITO': return 'Conceito';
      case 'CURSO': return 'Curso';
      case 'LIVRO': return 'Livro';
    }
  }

  get progressPercent(): number {
    if (!this.topics.length) return 0;
    const done = this.topics.filter(t => t.status === 'CONCLUIDO').length;
    return Math.round((done / this.topics.length) * 100);
  }

  get totalLoggedHours(): number {
    return this.topics.reduce((sum, t) => sum + (t.loggedHours || 0), 0);
  }

  get rootTopics(): StudyTopic[] {
    return this.topics.filter(t => !t.parentId);
  }

  childrenOf(parentId: number): StudyTopic[] {
    return this.topics.filter(t => t.parentId === parentId);
  }

  trackByTopic = (_: number, t: StudyTopic) => t.id;
}
