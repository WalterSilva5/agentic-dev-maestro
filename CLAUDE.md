# Agentic Dev Maestro — Guia para Agentes de IA

## Visão Geral

Plataforma fullstack de gestão de projetos e estudos, com suporte a agentes de IA. Monorepo com múltiplos clientes:

- **Web Client** (`web-client/`) — NestJS 8 + Angular 20 (Docker)
- **Local Client** (`local-client/`) — Python desktop (PySide6 + FastAPI + SQLite)
- **MCP** (`mcp/`) — Servidores Model Context Protocol
- **OpenCode Tools** (`.opencode/`) — Ferramentas customizadas para agentes

---

## Estrutura do Repositório

```
agentic-dev-maestro/
├── web-client/            # Cliente web (NestJS + Angular)
│   ├── back/              # Backend NestJS 8 + Prisma 4.8 + MySQL 8
│   ├── front/             # Frontend Angular 20 + Tailwind + Capacitor
│   ├── docker-compose.yml # Docker Compose (MySQL, Redis, API, Frontend)
│   └── .env.example       # Template de variáveis de ambiente
│
├── local-client/          # Cliente desktop Python
│   ├── maestro_local/     # Código fonte Python
│   ├── pyproject.toml     # Configuração do projeto Python
│   └── run.sh             # Script de execução
│
├── .opencode/             # Ferramentas OpenCode para agentes
│   ├── tools/             # Custom tools (TypeScript)
│   ├── commands/          # Comandos customizados
│   └── skills/            # Skills de uso da plataforma
│
├── mcp/                   # Servidores MCP
├── docs/                  # Documentação e diagramas
├── CLAUDE.md              # Este arquivo
├── README.md              # Readme geral do projeto
└── opencode.jsonc          # Config do OpenCode
```

---

## Regra Fundamental: Backend e Frontend Devem Estar Sincronizados

**Toda alteração em um lado DEVE ser refletida no outro.**

**Checklist para qualquer mudança de dados:**

1. `web-client/back/prisma/schema.prisma` — adicionar/alterar campo
2. `cd web-client/back && npx prisma migrate dev --name <descricao>`
3. DTOs em `web-client/back/src/modules/<modulo>/dto/`
4. Repository em `web-client/back/src/modules/<modulo>/`
5. Service e Controller do módulo
6. Frontend model — `web-client/front/src/app/models/`
7. Frontend service/API — `web-client/front/src/app/services/`
8. Frontend templates/páginas

---

## Web Client (`web-client/`)

### Stack

- **Backend**: NestJS 8 + Prisma 4.8 + MySQL 8 + Bull/Redis
- **Frontend**: Angular 20 (standalone) + Tailwind + NgRx + Capacitor

### Funcionalidades

- Autenticação (JWT local + refresh, Google OAuth, reset de senha)
- CRUD de projetos com kanban board
- Tasks com prioridade, tipo, labels, checklist, dependências
- Módulo de estudos (planos, tópicos, sessões)
- Comentários (markdown, code reviews)
- Documentos e atividade
- Dashboard e métricas

### Executar com Docker

```bash
cd web-client
cp .env.example .env
docker compose up --build
# Frontend: :4200 · API: :5000/api · Swagger: :5000/api/docs
```

### Executar localmente

```bash
cd web-client/back
npm install --legacy-peer-deps
npx prisma generate
npx prisma migrate deploy
npm run prisma:seed
npm run start:dev

cd web-client/front
npm install --legacy-peer-deps
npm start
```

---

## Local Client (`local-client/`)

### Stack

- Python 3.10+ com PySide6 (Qt 6) para GUI desktop
- FastAPI + uvicorn para API REST embutida
- SQLAlchemy 2.0 + SQLite para banco local

### Executar

```bash
cd local-client
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m maestro_local          # porta 9777
```

### API local

Endpoints sem autenticação em `http://127.0.0.1:9777/api`:
- `GET/POST /api/projects` — CRUD de projetos
- `GET /api/projects/{id}/board` — board kanban
- `GET/POST /api/tasks` — CRUD de tarefas
- `POST/GET /api/study/plans` — planos de estudo
- `POST/GET /api/study/sessions` — sessões de estudo
- `GET /api/study/stats` — estatísticas

---

## OpenCode Tools (`.opencode/`)

Ferramentas customizadas para agentes de IA interagirem com a plataforma via terminal.

### Ferramentas disponíveis

- `maestro_board` — Consultar board kanban
- `maestro_createTask` / `maestro_updateTask` / `maestro_deleteTask` — CRUD de tarefas
- `maestro_addComment` — Postar comentários (markdown, code reviews)
- `maestro_getFlow` — Exportar fluxo em mermaid
- `maestro_createDocument` — Criar documentos
- `maestro_addSubtask` — Adicionar subtarefas

### Comandos

- `/review <task>` — Code review de uma tarefa
- `/decompose <task>` — Decompor em subtarefas

---

## Convenções

- Commits e branches em português
- Código em inglês; UI em português brasileiro
- Nunca commitar `.env` real
- Backend: controller fino, service com lógica, repository com queries
- Frontend: standalone components, services injetáveis, NgRx para auth
