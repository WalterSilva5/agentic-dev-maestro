import { CommonModule } from '@angular/common';
import { Component, Input, OnChanges } from '@angular/core';

import { TaskFlow } from '../../models/maestro.models';

interface VNode {
  id: string;
  x: number;
  y: number;
  w: number;
  h: number;
  fill: string;
  stroke: string;
  line1: string;
  line2: string;
  pill: boolean;
}
interface VEdge {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

// Tema CLARO: chips com fundo claro tingido + borda colorida + texto escuro.
const STATE_FILL: Record<string, string> = {
  done: '#dcfce7',
  doing: '#fef3c7',
  blocked: '#fee2e2',
  todo: '#f3f4f6',
  entry: '#e0e7ff',
  exit: '#ede9fe'
};
const STATE_STROKE: Record<string, string> = {
  done: '#16a34a',
  doing: '#d97706',
  blocked: '#dc2626',
  todo: '#9ca3af',
  entry: '#6366f1',
  exit: '#8b5cf6'
};

// Renderiza o fluxo da tarefa (objetivo -> subtarefas -> aceite) como SVG.
// Layout em colunas por profundidade (sem dependências externas).
@Component({
  selector: 'app-flow-graph',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flow-wrap" *ngIf="vnodes.length; else empty">
      <svg [attr.viewBox]="'0 0 ' + width + ' ' + height" width="100%" [attr.height]="height" role="img">
        <defs>
          <marker id="fg-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
            <path d="M0,0 L8,4 L0,8 Z" fill="#9aa0a6" />
          </marker>
        </defs>
        <line
          *ngFor="let e of vedges"
          [attr.x1]="e.x1" [attr.y1]="e.y1" [attr.x2]="e.x2" [attr.y2]="e.y2"
          stroke="#9aa0a6" stroke-width="1.5" marker-end="url(#fg-arrow)"
        />
        <g *ngFor="let n of vnodes">
          <rect
            [attr.x]="n.x" [attr.y]="n.y" [attr.width]="n.w" [attr.height]="n.h"
            [attr.rx]="n.pill ? 22 : 8"
            [attr.fill]="n.fill" [attr.stroke]="n.stroke" stroke-width="1.5"
          />
          <text [attr.x]="n.x + n.w / 2" [attr.y]="n.y + (n.line2 ? 21 : 28)" text-anchor="middle"
                font-size="11" fill="#6b7280">{{ n.line1 }}</text>
          <text *ngIf="n.line2" [attr.x]="n.x + n.w / 2" [attr.y]="n.y + 37" text-anchor="middle"
                font-size="12" fill="#111827">{{ n.line2 }}</text>
        </g>
      </svg>
      <div class="flow-legend">
        <span><i style="background:#16a34a"></i> concluída</span>
        <span><i style="background:#d97706"></i> em andamento</span>
        <span><i style="background:#dc2626"></i> bloqueada</span>
        <span><i style="background:#9ca3af"></i> a fazer</span>
      </div>
    </div>
    <ng-template #empty><p class="flow-empty">Sem fluxo para exibir.</p></ng-template>
  `,
  styles: [
    `
      .flow-wrap { overflow-x: auto; }
      .flow-legend { display: flex; gap: 1rem; flex-wrap: wrap; font-size: 12px; color: #6b7280; margin-top: .5rem; }
      .flow-legend i { display: inline-block; width: 10px; height: 10px; border-radius: 3px; vertical-align: middle; margin-right: 4px; }
      .flow-empty { color: #6b7280; font-size: 13px; }
    `
  ]
})
export class FlowGraphComponent implements OnChanges {
  @Input() flow: TaskFlow | null = null;

  vnodes: VNode[] = [];
  vedges: VEdge[] = [];
  width = 0;
  height = 0;

  private readonly W = 160;
  private readonly H = 50;
  private readonly GX = 70;
  private readonly GY = 18;
  private readonly M = 12;

  ngOnChanges(): void {
    this.build();
  }

  private build(): void {
    this.vnodes = [];
    this.vedges = [];
    if (!this.flow || !this.flow.nodes?.length) return;

    const nodes = this.flow.nodes;
    const edges = this.flow.edges ?? [];
    const out = new Map<string, string[]>();
    const indeg = new Map<string, number>();
    nodes.forEach((n) => indeg.set(n.id, 0));
    edges.forEach((e) => {
      out.set(e.from, [...(out.get(e.from) ?? []), e.to]);
      indeg.set(e.to, (indeg.get(e.to) ?? 0) + 1);
    });

    // profundidade = maior caminho desde uma raiz (Kahn)
    const depth = new Map<string, number>();
    const queue = nodes.filter((n) => (indeg.get(n.id) ?? 0) === 0).map((n) => n.id);
    queue.forEach((id) => depth.set(id, 0));
    const localIndeg = new Map(indeg);
    const q = [...queue];
    while (q.length) {
      const cur = q.shift() as string;
      const d = depth.get(cur) ?? 0;
      for (const nx of out.get(cur) ?? []) {
        depth.set(nx, Math.max(depth.get(nx) ?? 0, d + 1));
        localIndeg.set(nx, (localIndeg.get(nx) ?? 0) - 1);
        if ((localIndeg.get(nx) ?? 0) <= 0) q.push(nx);
      }
    }
    nodes.forEach((n) => { if (!depth.has(n.id)) depth.set(n.id, 0); });

    // agrupa por coluna (profundidade)
    const cols = new Map<number, string[]>();
    for (const n of nodes) {
      const d = depth.get(n.id) as number;
      cols.set(d, [...(cols.get(d) ?? []), n.id]);
    }

    const pos = new Map<string, { x: number; y: number }>();
    const maxDepth = Math.max(...nodes.map((n) => depth.get(n.id) as number), 0);
    let maxRows = 0;
    for (let d = 0; d <= maxDepth; d++) {
      const ids = cols.get(d) ?? [];
      maxRows = Math.max(maxRows, ids.length);
      ids.forEach((id, row) => {
        pos.set(id, {
          x: this.M + d * (this.W + this.GX),
          y: this.M + row * (this.H + this.GY)
        });
      });
    }

    this.width = this.M * 2 + (maxDepth + 1) * this.W + maxDepth * this.GX;
    this.height = this.M * 2 + maxRows * this.H + (maxRows - 1) * this.GY;

    const byId = new Map(nodes.map((n) => [n.id, n]));
    for (const n of nodes) {
      const p = pos.get(n.id) as { x: number; y: number };
      const kind = n.kind;
      const key = kind ?? n.state ?? 'todo';
      const fill = STATE_FILL[key] ?? STATE_FILL['todo'];
      const stroke = STATE_STROKE[key] ?? STATE_STROKE['todo'];
      this.vnodes.push({
        id: n.id,
        x: p.x,
        y: p.y,
        w: this.W,
        h: this.H,
        fill,
        stroke,
        pill: !!kind,
        line1: kind ? (kind === 'entry' ? 'objetivo' : 'aceite') : (n.code ?? ''),
        line2: this.trunc(kind ? (n.label ?? '') : (n.title ?? ''), 22)
      });
    }
    for (const e of edges) {
      const a = pos.get(e.from);
      const b = pos.get(e.to);
      if (!a || !b) continue;
      this.vedges.push({
        x1: a.x + this.W,
        y1: a.y + this.H / 2,
        x2: b.x - 2,
        y2: b.y + this.H / 2
      });
    }
    void byId;
  }

  private trunc(s: string, n: number): string {
    return s.length > n ? s.slice(0, n - 1) + '…' : s;
  }
}
