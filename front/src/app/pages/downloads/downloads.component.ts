import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

interface DownloadItem {
  id: string;
  title: string;
  description: string;
  filename: string;
  path: string;
  icon: string;
}

@Component({
  selector: 'app-downloads',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="min-h-screen bg-base-200 p-6">
      <div class="max-w-4xl mx-auto">
        <!-- Header -->
        <div class="mb-8">
          <h1 class="text-3xl font-bold text-gray-800">Downloads</h1>
          <p class="text-gray-500 mt-2">
            Baixe skills, guias e documentações da plataforma em formato Markdown.
          </p>
        </div>

        <!-- Lista de downloads -->
        <div class="grid gap-4">
          <div
            *ngFor="let item of items"
            class="card bg-white shadow-md hover:shadow-lg transition-shadow"
          >
            <div class="card-body flex flex-row items-center gap-4 p-5">
              <!-- Icon -->
              <div class="w-12 h-12 rounded-lg bg-[#1DB954]/10 flex items-center justify-center shrink-0">
                <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6 text-[#1DB954]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                  <line x1="16" y1="13" x2="8" y2="13"></line>
                  <line x1="16" y1="17" x2="8" y2="17"></line>
                  <polyline points="10 9 9 9 8 9"></polyline>
                </svg>
              </div>

              <!-- Info -->
              <div class="flex-1 min-w-0">
                <h2 class="text-lg font-semibold text-gray-800">{{ item.title }}</h2>
                <p class="text-sm text-gray-500 mt-1">{{ item.description }}</p>
                <span class="text-xs text-gray-400 mt-1 block">
                  Formato: Markdown (.md) &middot; {{ item.filename }}
                </span>
              </div>

              <!-- Download Button -->
              <a
                [href]="item.path"
                [download]="item.filename"
                class="btn btn-primary btn-sm gap-2 shrink-0"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                  <polyline points="7 10 12 15 17 10"></polyline>
                  <line x1="12" y1="15" x2="12" y2="3"></line>
                </svg>
                Download
              </a>
            </div>
          </div>
        </div>

        <!-- Info adicional -->
        <div class="mt-8 p-4 bg-white rounded-lg shadow-sm border border-gray-100">
          <p class="text-sm text-gray-500">
            <strong>Dica:</strong> Os arquivos estão em formato Markdown (.md), compatíveis com
            qualquer editor de texto ou visualizador como Typora, VS Code, Obsidian, etc.
            Você também pode importá-los diretamente em agentes de IA como contexto.
          </p>
        </div>
      </div>
    </div>
  `,
})
export class DownloadsComponent {
  items: DownloadItem[] = [
    {
      id: 'skill-uso',
      title: 'Skill de Uso da Plataforma',
      description: 'Guia completo de uso do Agentic Dev Maestro: primeiros passos, tarefas, kanban, API keys, MCP, webhooks e boas práticas.',
      filename: 'skill-uso-plataforma.md',
      path: '/skills/skill-uso-plataforma.md',
      icon: 'document',
    },
  ];
}
