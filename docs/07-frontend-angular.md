# 07 — Frontend Angular

Decisão [D1](06-decisoes-em-aberto.md#d1--frontend-angular-ou-react--decidido-angular):
o front é **Angular** (`front/` do template). Remover `front-react/` e `front-flutter/`.

## Stack

| Item | Tecnologia |
|---|---|
| Framework | Angular 20 (standalone components, sem NgModules) |
| Estado | NgRx (store por feature) + signals para estado local |
| Estilo | Tailwind CSS + Bootstrap (já no template) |
| Drag-and-drop | **Angular CDK** (`@angular/cdk/drag-drop`) — para o kanban |
| Grafo de fluxo | **`@swimlane/ngx-graph`** (dagre) — fluxograma da tarefa (doc 08) |
| Markdown | `ngx-markdown` (render) + editor de textarea com preview |
| Alertas | SweetAlert2 (já no template) |
| HTTP | `HttpClient` + interceptors (JWT, refresh, X-Company-Id, erros) |
| PWA/Mobile | Capacitor (já no template) |

> Onde o template já entrega login/refresh/perfil, **reusar** — só adicionar o domínio.

## Estrutura de pastas (feature-based)

```
front/src/app/
├── core/                  # singletons: guards, interceptors, auth, config
│   ├── auth/              # (do template) login, refresh, guard
│   ├── interceptors/      # jwt, company-context (X-Company-Id), error
│   └── tenant/            # serviço de empresa ativa (signal)
├── shared/                # componentes/pipes/diretivas reutilizáveis
│   └── ui/                # botões, modal, badge de prioridade, avatar...
├── features/
│   ├── companies/         # listar/selecionar/criar empresa, membros
│   ├── projects/          # listar/criar projeto
│   ├── board/             # quadro kanban (DnD)
│   ├── tasks/             # detalhe/edição de tarefa + subtarefas
│   ├── docs/              # editor/visualizador markdown
│   └── settings/          # membros, API keys
└── state/                 # NgRx (actions/reducers/effects/selectors) por feature
```

## Contexto de empresa (multi-tenant no front)

- Um `TenantService` guarda a **empresa ativa** (signal), persistida em storage.
- Um **interceptor** injeta `X-Company-Id` em toda requisição.
- Um **seletor de empresa** no header troca o contexto (o usuário pode ter várias).
- Trocar de empresa limpa os stores de domínio (board/tasks) e refaz o fetch.

Ver fluxo de auth/contexto em [`diagramas/auth-rbac.svg`](diagramas/auth-rbac.svg).

## Quadro kanban (CDK drag-drop)

Componentes:

- `BoardComponent` — carrega o board (colunas + tarefas) via NgRx; orquestra DnD.
- `ColumnComponent` — uma coluna (`cdkDropList`), aceita drop e mostra WIP.
- `TaskCardComponent` — cartão (`cdkDrag`): título, código `GAV-42`, assignee,
  prioridade, estimativa (hd), labels.
- `TaskDetailComponent` — modal/painel: edição, subtarefas, comentários, docs, atividade.

Comportamento do drop:

1. `cdkDropListDropped` → **atualização otimista** no store (move o cartão na UI).
2. Dispara `POST /tasks/:code/move { columnId, rank }`.
3. Em erro → **rollback** + SweetAlert. Em sucesso → confirma o `rank` do servidor.
4. `rank` lexicográfico (ver [D4](06-decisoes-em-aberto.md#d4--ordenação-no-kanban-rank-fracionário-lexorank-vs-order-inteiro)) → mover = 1 PATCH.

## Fluxo da tarefa (`ngx-graph`)

Visualização do fluxo objetivo → subtarefas → aceite (conceito no [doc 08](08-fluxo-de-tarefas.md)).

- **Lib:** `@swimlane/ngx-graph` (layout dagre, pan/zoom, template de nó próprio).
- `TaskFlowComponent` — consome `GET /tasks/:code/flow` (`{ nodes, edges }`) e desenha
  o DAG. Vive numa aba do `TaskDetailComponent` ("Fluxo"), ao lado de "Subtarefas".
- **Template de nó:** título, código `GAV-42`, assignee, **cor por status** e cadeado
  quando `bloqueada`; nós sintéticos **Objetivo** (entrada) e **Aceite** (saída).
- **Interações:**
  - clicar nó → abre o detalhe da subtarefa;
  - arrastar de um nó a outro → `POST /dependencies` (cria aresta, valida ciclo);
  - mover subtarefa no kanban → recolore o nó (deriva do mesmo status).
- **Sem dependências** → render padrão `entrada → (subtarefas em paralelo) → aceite`.
- O mesmo componente serve ao **fluxo do projeto** (nós = tarefas), trocando a fonte.
- **Export:** botão "exportar Mermaid" usa `?format=mermaid` para embutir o fluxo na
  doc markdown da tarefa.

## Estado (NgRx)

- Um slice por feature: `companies`, `projects`, `board`, `tasks`, `docs`, `members`.
- Effects fazem as chamadas HTTP; selectors derivam a view (ex.: tarefas por coluna).
- Estado de UI efêmero (modais, drafts) fica em **signals** locais, fora do store.

## Documentos markdown

- `DocViewerComponent` — render com `ngx-markdown`.
- `DocEditorComponent` — editor com preview lado a lado + botão **exportar `.md`**
  (preserva o fluxo atual de mandar markdown para o time).
- Docs vivem em projeto e em tarefa (mesma entidade `Document`).

## Rotas (lazy)

```
/login                                  (template)
/companies                              seleção/criação de empresa
/:companyId/projects                    lista de projetos
/:companyId/projects/:id/board          quadro kanban
/:companyId/projects/:id/docs           documentos do projeto
/:companyId/tasks/:code                 detalhe da tarefa (deep-link GAV-42)
/:companyId/settings/members            gestão de membros e papéis
/:companyId/settings/api-keys           gestão de API keys (agentes)
```

Cada feature é **lazy-loaded** por rota. Guards: `authGuard` (template) + `tenantGuard`
(exige empresa ativa) + `roleGuard` (esconde telas de gestão para DEV/VIEWER).

## Integração com a API

- Gerar os **tipos/clients a partir do Swagger** da API (`openapi-generator` ou
  `ng-openapi-gen`) para não escrever DTOs à mão e manter o front em sincronia.
- Padronizar o tratamento de erro (interceptor) para mensagens vindas da API
  (escopo insuficiente, validação) virarem toasts amigáveis.

## Definition of Done (frontend)

- [ ] Login/refresh reusando o template, com seletor de empresa funcional.
- [ ] Quadro kanban com DnD, update otimista e rollback.
- [ ] Detalhe de tarefa com subtarefas, comentários e docs.
- [ ] Aba "Fluxo" (ngx-graph) com nós coloridos por status, clicáveis, e export Mermaid.
- [ ] Editor/visualizador markdown com export `.md`.
- [ ] Telas de membros e API keys protegidas por papel.
- [ ] Tipos gerados do Swagger; sem `any` nos contratos de API.
- [ ] Responsivo + dark mode; lint e build sem erros.
