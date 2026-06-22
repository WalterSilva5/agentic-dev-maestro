import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import Swal from 'sweetalert2';

import { MaestroApiService } from '../../services/maestro-api.service';
import {
  ActivityItem,
  Comment,
  DocItem,
  Task,
  TaskFlow,
} from '../../models/maestro.models';
import { FlowGraphComponent } from '../../components/flow-graph/flow-graph.component';

// Aba ativa da página de detalhe.
type DetailTab = 'fluxo' | 'comentarios' | 'documentos' | 'atividade';

@Component({
  selector: 'app-task-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, FlowGraphComponent],
  templateUrl: './task-detail.component.html',
  styleUrls: ['./task-detail.component.scss'],
})
export class TaskDetailComponent implements OnInit {
  // Param de rota 'code' via withComponentInputBinding.
  @Input() set code(value: string | undefined) {
    this._code = value;
    if (value) this.load();
  }
  get code(): string | undefined {
    return this._code;
  }
  private _code?: string;

  loading = false;

  task: Task | null = null;
  flow: TaskFlow | null = null;
  comments: Comment[] = [];
  docs: DocItem[] = [];
  activity: ActivityItem[] = [];

  tab: DetailTab = 'fluxo';

  // Formulário de comentário.
  commentText = '';
  postingComment = false;

  // Formulário de documento.
  newDocTitle = '';
  newDocBody = '';
  newDocType: DocItem['type'] = 'NOTES';
  docTypes: DocItem['type'][] = ['SPEC', 'PLAN', 'NOTES', 'ADR', 'OTHER'];
  savingDoc = false;

  constructor(private api: MaestroApiService) {}

  ngOnInit(): void {
    if (this._code && !this.task) this.load();
  }

  async load(): Promise<void> {
    const code = this._code;
    if (!code) return;
    this.loading = true;
    try {
      this.task = await this.api.getTask(code);
      this.flow = await this.api.getFlow(code);
      this.comments = await this.api.listComments(this.task.id);
      this.docs = await this.api.listDocuments({ taskId: this.task.id });
      this.activity = await this.api.listActivity({
        entityType: 'Task',
        entityId: this.task.id,
        limit: 20,
      });
    } catch (err) {
      console.error('load task detail error', err);
      Swal.fire({
        icon: 'error',
        title: 'Erro',
        text: 'Não foi possível carregar os detalhes da tarefa.',
      });
    } finally {
      this.loading = false;
    }
  }

  setTab(tab: DetailTab): void {
    this.tab = tab;
  }

  // ---- Badges ----

  priorityClass(priority?: Task['priority']): string {
    switch (priority) {
      case 'URGENT':
        return 'badge-error';
      case 'HIGH':
        return 'badge-warning';
      case 'MEDIUM':
        return 'badge-info';
      default:
        return 'badge-ghost';
    }
  }

  // ---- Helpers de exibição ----

  authorName(c: Comment): string {
    if (c.author) {
      return `${c.author.firstName ?? ''} ${c.author.lastName ?? ''}`.trim() || 'Usuário';
    }
    return c.viaApiKeyId ? 'Agente' : 'Usuário';
  }

  shortDate(iso?: string): string {
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    const now = Date.now();
    const diff = now - d.getTime();
    const min = Math.round(diff / 60000);
    if (min < 1) return 'agora';
    if (min < 60) return `há ${min} min`;
    const hours = Math.round(min / 60);
    if (hours < 24) return `há ${hours} h`;
    const days = Math.round(hours / 24);
    if (days < 7) return `há ${days} d`;
    return d.toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  }

  exportUrl(id: number): string {
    return this.api.exportDocumentUrl(id);
  }

  trackByComment = (_: number, c: Comment) => c.id;
  trackByDoc = (_: number, d: DocItem) => d.id;
  trackByActivity = (_: number, a: ActivityItem) => a.id;

  // ---- Ações ----

  async addComment(): Promise<void> {
    const body = this.commentText.trim();
    if (!body || !this.task) return;
    this.postingComment = true;
    try {
      await this.api.createComment(this.task.id, body);
      this.commentText = '';
      this.comments = await this.api.listComments(this.task.id);
    } catch (err) {
      console.error('createComment error', err);
      Swal.fire({
        icon: 'error',
        title: 'Erro',
        text: 'Não foi possível enviar o comentário.',
      });
    } finally {
      this.postingComment = false;
    }
  }

  async addDocument(): Promise<void> {
    const title = this.newDocTitle.trim();
    const body = this.newDocBody.trim();
    if (!title || !this.task) {
      Swal.fire({
        icon: 'warning',
        title: 'Título obrigatório',
        text: 'Informe o título do documento.',
      });
      return;
    }
    this.savingDoc = true;
    try {
      await this.api.createDocument({
        title,
        body,
        type: this.newDocType,
        taskId: this.task.id,
      });
      this.newDocTitle = '';
      this.newDocBody = '';
      this.newDocType = 'NOTES';
      this.docs = await this.api.listDocuments({ taskId: this.task.id });
    } catch (err) {
      console.error('createDocument error', err);
      Swal.fire({
        icon: 'error',
        title: 'Erro',
        text: 'Não foi possível criar o documento.',
      });
    } finally {
      this.savingDoc = false;
    }
  }
}
