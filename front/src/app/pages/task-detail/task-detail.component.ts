import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import Swal from 'sweetalert2';

import { MaestroApiService } from '../../services/maestro-api.service';
import { TenantService } from '../../services/tenant.service';
import {
  ActivityItem,
  Comment,
  DocItem,
  Label,
  Member,
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

  // Modo de edição.
  editMode = false;
  editForm: Partial<Task> = {};
  saving = false;

  // Prioridades disponíveis.
  priorities: Task['priority'][] = ['LOW', 'MEDIUM', 'HIGH', 'URGENT'];

  // Formulário de comentário.
  commentText = '';
  postingComment = false;

  // Formulário de documento.
  newDocTitle = '';
  newDocBody = '';
  newDocType: DocItem['type'] = 'NOTES';
  docTypes: DocItem['type'][] = ['SPEC', 'PLAN', 'NOTES', 'ADR', 'OTHER'];
  savingDoc = false;

  // Labels e assignee.
  allLabels: Label[] = [];
  members: Member[] = [];

  constructor(private api: MaestroApiService, private tenant: TenantService) {}

  ngOnInit(): void {
    if (this._code && !this.task) this.load();
  }

  async load(): Promise<void> {
    const code = this._code;
    if (!code) return;
    this.loading = true;
    try {
      this.task = await this.api.getTask(code);
      const cid = this.tenant.companyId;
      const [flow, comments, docs, activity, labels, members] = await Promise.all([
        this.api.getFlow(code),
        this.api.listComments(this.task.id),
        this.api.listDocuments({ taskId: this.task.id }),
        this.api.listActivity({ entityType: 'Task', entityId: this.task.id, limit: 20 }),
        this.api.listLabels().catch(() => [] as Label[]),
        cid ? this.api.listMembers(cid).catch(() => [] as Member[]) : Promise.resolve([] as Member[]),
      ]);
      this.flow = flow;
      this.comments = comments;
      this.docs = docs;
      this.activity = activity;
      this.allLabels = labels;
      this.members = members;
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

  // ---- Edição ----

  toggleEdit(): void {
    if (this.editMode) {
      this.editMode = false;
      return;
    }
    this.editForm = {
      title: this.task?.title,
      description: this.task?.description,
      objective: this.task?.objective,
      acceptance: this.task?.acceptance,
      priority: this.task?.priority,
      estimateMd: this.task?.estimateMd,
    };
    this.editMode = true;
  }

  cancelEdit(): void {
    this.editMode = false;
    this.editForm = {};
  }

  async saveEdit(): Promise<void> {
    if (!this.task || !this.code) return;
    this.saving = true;
    try {
      await this.api.updateTask(this.code, this.editForm);
      this.editMode = false;
      this.editForm = {};
      await this.load();
    } catch (err) {
      console.error('updateTask error', err);
      Swal.fire({ icon: 'error', title: 'Erro', text: 'Não foi possível salvar as alterações.' });
    } finally {
      this.saving = false;
    }
  }

  async confirmDelete(): Promise<void> {
    if (!this.task || !this.code) return;
    const result = await Swal.fire({
      icon: 'warning',
      title: 'Excluir tarefa?',
      text: `Tem certeza que deseja excluir ${this.code}? Esta ação não pode ser desfeita.`,
      showCancelButton: true,
      confirmButtonText: 'Excluir',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#d33',
    });
    if (!result.isConfirmed) return;
    try {
      await this.api.deleteTask(this.code);
      Swal.fire({
        icon: 'success',
        title: 'Tarefa excluída',
        text: `${this.code} foi excluída com sucesso.`,
        timer: 2000,
        showConfirmButton: false,
      });
      window.history.back();
    } catch (err) {
      console.error('deleteTask error', err);
      Swal.fire({ icon: 'error', title: 'Erro', text: 'Não foi possível excluir a tarefa.' });
    }
  }

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

  // ---- Labels ----

  get availableLabels(): Label[] {
    const applied = new Set((this.task?.labels ?? []).map((l) => l.id));
    return this.allLabels.filter((l) => !applied.has(l.id));
  }

  async addLabel(labelId: number): Promise<void> {
    if (!this.task) return;
    try {
      await this.api.applyLabel(labelId, this.task.id);
      await this.load();
    } catch {
      Swal.fire({ icon: 'error', title: 'Erro', text: 'Não foi possível aplicar a label.' });
    }
  }

  async removeTaskLabel(labelId: number): Promise<void> {
    if (!this.task) return;
    try {
      await this.api.removeLabel(labelId, this.task.id);
      await this.load();
    } catch {
      Swal.fire({ icon: 'error', title: 'Erro', text: 'Não foi possível remover a label.' });
    }
  }

  // ---- Assignee ----

  assigneeName(): string {
    const a = this.task?.assignee;
    if (!a) return 'Sem responsável';
    return `${a.firstName} ${a.lastName}`.trim();
  }

  async changeAssignee(userId: string): Promise<void> {
    if (!this.task || !this.code) return;
    const assigneeId = userId ? Number(userId) : null;
    try {
      await this.api.updateTask(this.code, { assigneeId } as any);
      await this.load();
    } catch {
      Swal.fire({ icon: 'error', title: 'Erro', text: 'Não foi possível alterar o responsável.' });
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
