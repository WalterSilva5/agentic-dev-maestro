# Tarefas — Frontend (Angular 20)

Base: `front/` do template (login/refresh/perfil prontos). Arquitetura no
[doc 07](../07-frontend-angular.md). Esforço em homem-dia (hd).

---

## Fase 1 — Núcleo de tarefas e quadro

### F1.0 — Setup e limpeza · 0.5 hd
- [ ] Copiar `front/` do template; remover `front-react/` e `front-flutter/`
- [ ] Subir o front e validar login contra a API
- [ ] Instalar deps novas: `@angular/cdk`, `ngx-markdown`, `@swimlane/ngx-graph`

### F1.1 — Contexto de empresa (multi-tenant) · 1.5 hd
- [ ] `TenantService` com empresa ativa (signal + storage)
- [ ] Interceptor que injeta `X-Company-Id`
- [ ] Seletor de empresa no header; trocar limpa stores de domínio
- [ ] `tenantGuard` (exige empresa ativa)

### F1.2 — Lista/criação de projetos · 1.5 hd
- [ ] Tela de projetos (lista + criar)
- [ ] Slice NgRx `projects` (effects + selectors)
- [ ] Navegação para o board do projeto

### F1.3 — Quadro kanban com CDK drag-drop · 4 hd
- [ ] `BoardComponent` carregando colunas + tarefas (slice `board`)
- [ ] `ColumnComponent` (`cdkDropList`) com indicador de WIP
- [ ] `TaskCardComponent` (`cdkDrag`): código, assignee, prioridade, estimativa, labels
- [ ] Drop → **update otimista** + `POST /move` + **rollback** em erro
- [ ] Criar tarefa rápida na coluna (inline)

### F1.4 — Detalhe da tarefa · 2.5 hd
- [ ] `TaskDetailComponent` (modal/painel): editar campos, prioridade, estimativa
- [ ] Campos **objetivo** e **critério de aceite** (markdown)
- [ ] Subtarefas (listar/criar/concluir)
- [ ] Comentários
- [ ] Deep-link `/:companyId/tasks/:code`

### F1.5 — Aba de fluxo da tarefa (ngx-graph) · 3 hd
> Feature do [doc 08](../08-fluxo-de-tarefas.md).
- [ ] `TaskFlowComponent` consumindo `GET /tasks/:code/flow` (`{ nodes, edges }`)
- [ ] Template de nó: título, código, assignee, **cor por status** + cadeado se bloqueada
- [ ] Nós sintéticos **Objetivo** (entrada) e **Aceite** (saída)
- [ ] Clicar nó → abre subtarefa; layout dagre + pan/zoom
- [ ] Arrastar nó→nó → `POST /dependencies` (com feedback de ciclo inválido)
- [ ] Botão **exportar Mermaid** (`?format=mermaid`)
- [ ] Reuso para **fluxo do projeto** (nós = tarefas)

---

## Fase 2 — Docs e atividade

### F2.1 — Documentos markdown · 2.5 hd
- [ ] `DocViewerComponent` (render `ngx-markdown`)
- [ ] `DocEditorComponent` (edição + preview lado a lado)
- [ ] Botão **exportar `.md`**
- [ ] Docs no projeto e na tarefa

### F2.2 — Aba de atividade/auditoria · 1.5 hd
- [ ] Timeline de `ActivityLog` na tarefa e no projeto
- [ ] Badge "via agente" quando a ação veio de API key

---

## Fase 4 — Settings e visão

### F4.1 — Gestão de membros · 1.5 hd
- [ ] Tela de membros (listar, convidar, mudar papel, remover)
- [ ] `roleGuard` esconde gestão para DEV/VIEWER

### F4.2 — Gestão de API keys · 1.5 hd
- [ ] Listar chaves (label, prefixo, lastUsed, expira)
- [ ] Criar chave → mostrar segredo **uma vez** (copiar) + escolher escopos
- [ ] Revogar chave

### F4.3 — Dashboard do gerente · 2.5 hd
- [ ] Progresso por projeto/empresa (tarefas por status, por assignee)
- [ ] Filtros e busca (status, label, assignee, texto)

---

## Transversal

### FX.1 — Tipos gerados do Swagger · 1 hd
- [ ] Configurar `ng-openapi-gen` (ou `openapi-generator`) apontando para `/api/docs-json`
- [ ] Script `npm run gen:api` + usar os tipos nos services

### FX.2 — UX e tema · 1 hd
- [ ] Responsivo + dark mode
- [ ] Tratamento de erro padronizado (interceptor → toasts SweetAlert2)

---

## Checklist de qualidade (frontend)

- [ ] Kanban com DnD fluido, update otimista e rollback testado
- [ ] Nenhum `any` nos contratos de API (tipos do Swagger)
- [ ] Telas de gestão protegidas por papel
- [ ] Segredo de API key exibido só uma vez, com copiar
- [ ] Lazy loading por rota; lint e build sem erros
- [ ] Responsivo e dark mode validados
