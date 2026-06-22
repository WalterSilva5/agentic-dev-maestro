import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import * as M from '../models/maestro.models';
import { ConfigService } from './config.service';

// Cliente único da API do domínio. Auth (Bearer) e X-Company-Id são adicionados
// pelos interceptors (auth + tenant). Métodos retornam Promises.
@Injectable({ providedIn: 'root' })
export class MaestroApiService {
  constructor(private http: HttpClient, private config: ConfigService) {}

  private get base(): string {
    return this.config.apiUrl;
  }

  private qs(params: Record<string, unknown>): string {
    const sp = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== '') sp.set(k, String(v));
    }
    const s = sp.toString();
    return s ? `?${s}` : '';
  }

  private get<T>(path: string): Promise<T> {
    return firstValueFrom(this.http.get<T>(this.base + path));
  }
  private post<T>(path: string, body?: unknown, headers?: Record<string, string>): Promise<T> {
    return firstValueFrom(this.http.post<T>(this.base + path, body ?? {}, headers ? { headers } : {}));
  }
  private put<T>(path: string, body?: unknown): Promise<T> {
    return firstValueFrom(this.http.put<T>(this.base + path, body ?? {}));
  }
  private patch<T>(path: string, body?: unknown): Promise<T> {
    return firstValueFrom(this.http.patch<T>(this.base + path, body ?? {}));
  }
  private del<T>(path: string): Promise<T> {
    return firstValueFrom(this.http.delete<T>(this.base + path));
  }

  // ---- empresas ----
  listCompanies() { return this.get<M.Company[]>('/companies'); }
  createCompany(b: { name: string; slug?: string }) { return this.post<M.Company>('/companies', b); }

  // ---- membros ----
  listMembers(cid: number) { return this.get<M.Member[]>(`/companies/${cid}/members`); }
  addMember(cid: number, b: { email: string; role?: string }) { return this.post<M.Member>(`/companies/${cid}/members`, b); }
  updateMemberRole(cid: number, mid: number, role: string) { return this.patch<M.Member>(`/companies/${cid}/members/${mid}`, { role }); }
  removeMember(cid: number, mid: number) { return this.del<unknown>(`/companies/${cid}/members/${mid}`); }

  // ---- API keys ----
  listApiKeys(cid: number) { return this.get<M.ApiKeyInfo[]>(`/companies/${cid}/api-keys`); }
  createApiKey(cid: number, b: { label: string; scopes?: string[]; expiresAt?: string }) { return this.post<M.ApiKeyInfo>(`/companies/${cid}/api-keys`, b); }
  revokeApiKey(cid: number, id: number) { return this.del<unknown>(`/companies/${cid}/api-keys/${id}`); }

  // ---- projetos ----
  listProjects() { return this.get<M.Project[]>('/projects'); }
  createProject(b: { name: string; key: string; description?: string }) { return this.post<M.Project>('/projects', b); }
  getBoard(pid: number) { return this.get<M.Board>(`/projects/${pid}/board`); }

  // ---- tarefas ----
  listTasks(filters: Record<string, unknown> = {}) { return this.get<M.Task[]>('/tasks' + this.qs(filters)); }
  getTask(code: string) { return this.get<M.Task>(`/tasks/${code}`); }
  createTask(b: Partial<M.Task> & { projectId: number; title: string }) { return this.post<M.Task>('/tasks', b); }
  moveTask(code: string, columnId: number) { return this.post<M.Task>(`/tasks/${code}/move`, { columnId }); }
  bulkTasks(b: unknown, idempotencyKey?: string) { return this.post<M.Task[]>('/tasks/bulk', b, idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : undefined); }
  getFlow(code: string) { return this.get<M.TaskFlow>(`/tasks/${code}/flow`); }
  addDependency(code: string, blockerCode: string) { return this.post<unknown>(`/tasks/${code}/dependencies`, { blockerCode }); }
  removeDependency(code: string, depId: number) { return this.del<unknown>(`/tasks/${code}/dependencies/${depId}`); }

  // ---- labels ----
  listLabels() { return this.get<M.Label[]>('/labels'); }
  createLabel(b: { name: string; color?: string }) { return this.post<M.Label>('/labels', b); }
  applyLabel(labelId: number, taskId: number) { return this.post<unknown>(`/labels/${labelId}/tasks/${taskId}`); }
  removeLabel(labelId: number, taskId: number) { return this.del<unknown>(`/labels/${labelId}/tasks/${taskId}`); }

  // ---- documentos ----
  listDocuments(filters: { projectId?: number; taskId?: number }) { return this.get<M.DocItem[]>('/documents' + this.qs(filters)); }
  createDocument(b: { title: string; body: string; type?: string; projectId?: number; taskId?: number }) { return this.post<M.DocItem>('/documents', b); }
  updateDocument(id: number, b: { title?: string; body?: string; type?: string }) { return this.put<M.DocItem>(`/documents/${id}`, b); }
  deleteDocument(id: number) { return this.del<unknown>(`/documents/${id}`); }
  exportDocumentUrl(id: number) { return `${this.base}/documents/${id}/export`; }

  // ---- comentários ----
  listComments(taskId: number) { return this.get<M.Comment[]>(`/comments${this.qs({ taskId })}`); }
  createComment(taskId: number, body: string) { return this.post<M.Comment>('/comments', { taskId, body }); }

  // ---- auditoria ----
  listActivity(filters: { entityType?: string; entityId?: number; limit?: number } = {}) { return this.get<M.ActivityItem[]>('/activity' + this.qs(filters)); }
}
