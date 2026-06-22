import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import Swal from 'sweetalert2';

import { MaestroApiService } from '../../services/maestro-api.service';
import { TenantService } from '../../services/tenant.service';
import { Board, BoardColumn, Task } from '../../models/maestro.models';

// Origem de um card sendo arrastado (DnD nativo HTML5).
interface DragSource {
  code: string;
  columnId: number;
}

@Component({
  selector: 'app-board',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './board.component.html',
  styleUrl: './board.component.scss',
})
export class BoardComponent implements OnInit {
  // Param de rota 'id' via withComponentInputBinding.
  @Input() id?: string;

  projectId = 0;
  board: Board | null = null;
  loading = false;

  // Estado do drag-and-drop nativo.
  private dragging: DragSource | null = null;
  dragOverColumnId: number | null = null;

  // Texto do input "adicionar tarefa" por coluna (keyed por columnId).
  newTaskTitle: Record<number, string> = {};

  constructor(
    private api: MaestroApiService,
    protected tenant: TenantService,
  ) {}

  get hasCompany(): boolean {
    return this.tenant.companyId != null;
  }

  ngOnInit(): void {
    this.projectId = Number(this.id);
    if (this.hasCompany && this.projectId) {
      this.loadBoard();
    }
  }

  async loadBoard(): Promise<void> {
    if (!this.projectId) return;
    this.loading = true;
    try {
      this.board = await this.api.getBoard(this.projectId);
    } catch (err) {
      console.error('getBoard error', err);
      Swal.fire({ icon: 'error', title: 'Erro', text: 'Não foi possível carregar o board.' });
    } finally {
      this.loading = false;
    }
  }

  trackByColumn = (_: number, c: BoardColumn) => c.id;
  trackByTask = (_: number, t: Task) => t.code;

  priorityClass(priority: Task['priority']): string {
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

  // ---- Drag and drop ----

  onDragStart(task: Task): void {
    this.dragging = { code: task.code, columnId: task.columnId };
  }

  onDragEnd(): void {
    this.dragging = null;
    this.dragOverColumnId = null;
  }

  onDragEnter(column: BoardColumn): void {
    this.dragOverColumnId = column.id;
  }

  onDragLeave(column: BoardColumn): void {
    if (this.dragOverColumnId === column.id) {
      this.dragOverColumnId = null;
    }
  }

  async onDrop(column: BoardColumn): Promise<void> {
    const drag = this.dragging;
    this.dragOverColumnId = null;
    if (!drag || !this.board) return;
    if (drag.columnId === column.id) {
      this.dragging = null;
      return;
    }

    // Localiza coluna de origem e o card.
    const fromColumn = this.board.columns.find((c) => c.id === drag.columnId);
    const card = fromColumn?.tasks.find((t) => t.code === drag.code);
    if (!fromColumn || !card) {
      this.dragging = null;
      return;
    }

    // Move otimista no modelo local.
    fromColumn.tasks = fromColumn.tasks.filter((t) => t.code !== drag.code);
    card.columnId = column.id;
    column.tasks = [...column.tasks, card];
    this.dragging = null;

    try {
      await this.api.moveTask(drag.code, column.id);
    } catch (err) {
      console.error('moveTask error', err);
      await this.loadBoard();
      Swal.fire({ icon: 'error', title: 'Erro', text: 'Não foi possível mover a tarefa.' });
    }
  }

  // ---- Add task ----

  async addTask(column: BoardColumn): Promise<void> {
    const title = (this.newTaskTitle[column.id] ?? '').trim();
    if (!title) return;
    try {
      await this.api.createTask({ projectId: this.projectId, title, columnId: column.id });
      this.newTaskTitle[column.id] = '';
      await this.loadBoard();
    } catch (err) {
      console.error('createTask error', err);
      Swal.fire({ icon: 'error', title: 'Erro', text: 'Não foi possível criar a tarefa.' });
    }
  }
}
