# Agentic Dev Maestro — Guia para Agentes de IA

## Visão Geral

O **Maestro Local** é uma aplicação desktop que combina gestão de tarefas kanban com ferramentas para agentes de IA. O agente cria, edita, move e comenta tarefas diretamente pelo terminal, enquanto o usuário acompanha pela interface gráfica.

- **Produto principal**: `local-client/` — Python desktop (PySide6 + FastAPI + SQLite)
- **Cliente web**: `web-client/` — NestJS + Angular (Docker, para deploy)
- **Ferramentas**: `.opencode/` — Tools customizadas para agentes

---

## Estrutura do Repositório

```
agentic-dev-maestro/
├── local-client/          # ← PRODUTO PRINCIPAL
│   ├── maestro_local/     # Código fonte Python
│   │   ├── api/app.py     # FastAPI — todos os endpoints
│   │   ├── db/models.py   # SQLAlchemy — modelos de dados
│   │   ├── gui/           # Interface desktop (PySide6)
│   │   │   ├── main_window.py
│   │   │   ├── theme.py   # Tema dark/light
│   │   │   └── views/     # Board, Tasks, Estudos, Métricas...
│   │   └── skills/        # Skills para agentes
│   ├── pyproject.toml
│   └── run.sh
│
├── web-client/            # Cliente web (secundário)
│   ├── back/              # NestJS 8 + Prisma + MySQL
│   ├── front/             # Angular 20 + Tailwind
│   └── docker-compose.yml
│
├── .opencode/             # Ferramentas para agentes
│   ├── tools/maestro.ts   # 12 tools customizadas
│   ├── commands/          # /review, /decompose
│   └── skills/            # Skill de uso da plataforma
│
├── mcp/                   # Servidor MCP
├── docs/                  # Documentação
├── CLAUDE.md              # Este arquivo
└── README.md              # Readme do projeto
```

---

## Local Client — O Produto Principal

### Executar

```bash
cd local-client
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m maestro_local          # porta 9777
```

### O que ele faz

**Para o usuário (GUI):**
- Board kanban com drag-and-drop
- Diário de trabalho com relatórios
- Planos de estudo com roadmap visual
- Métricas e dashboard
- Tema dark/light

**Para o agente (API):**
- CRUD completo de projetos e tarefas
- Move tarefas entre colunas
- Adiciona comentários (code reviews, commits)
- Cria e gerencia planos de estudo
- Consulta métricas e contexto

### API Local

Base URL: `http://127.0.0.1:9777/api` (sem autenticação)

| Recurso | Endpoints |
|---------|-----------|
| Projetos | `GET/POST /api/projects`, `GET /api/projects/{id}/board` |
| Tarefas | `POST/GET /api/tasks`, `GET/PATCH/DELETE /api/tasks/{code}` |
| Comentários | `GET/POST /api/comments`, `PATCH/DELETE /api/comments/{id}` |
| Estudos | `POST/GET /api/study/plans`, `GET/POST /api/study/plans/{id}/topics` |
| Sessões | `POST /api/study/sessions`, `GET /api/study/stats` |
| Documentos | `GET/POST /api/documents`, `PUT/DELETE /api/documents/{id}` |
| Labels | `POST/GET /api/labels`, `POST/DELETE /api/labels/{id}/tasks/{task_id}` |

---

## OpenCode Tools

Ferramentas customizadas para agentes de IA no terminal.

### Ferramentas disponíveis

- `maestro_listProjects` — Listar projetos
- `maestro_board` — Consultar board kanban
- `maestro_getTask` / `maestro_listTasks` — Detalhes e filtros de tarefas
- `maestro_createTask` / `maestro_updateTask` / `maestro_deleteTask` — CRUD
- `maestro_moveTask` — Mover entre colunas
- `maestro_addSubtask` — Adicionar subtarefa (só título)
- `maestro_addComment` — Comentário com markdown
- `maestro_getFlow` — Exportar fluxo em mermaid
- `maestro_createDocument` — Criar documento (spec, plan, ADR)

### Comandos

- `/review <task>` — Code review de uma tarefa
- `/decompose <task>` — Decompor em subtarefas

### Como usar

```bash
# No opencode:
"liste os projetos usando maestro_listProjects"
"crie uma tarefa 'Implementar busca' no projeto MAESTRO"
"adicione um comentário de code review na MAESTRO-10"
```

---

## Convenções

- Código em inglês; UI em português brasileiro
- Commits e branches em português
- Nunca commitar `.env` real
- API sem autenticação (app local, single-user)
- SQLite local (sem necessidade de Docker para o app principal)
