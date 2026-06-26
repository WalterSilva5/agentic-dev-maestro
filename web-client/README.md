# Web Client — Agentic Dev Maestro

Cliente web do Maestro. Backend NestJS 8 + Frontend Angular 20, rodando via Docker.

## Stack

- **Backend**: NestJS 8 + Prisma 4.8 + MySQL 8 + Bull/Redis
- **Frontend**: Angular 20 (standalone) + Tailwind CSS + NgRx + Capacitor

## Início Rápido

### Docker (recomendado)

```bash
cp .env.example .env
docker compose up --build
```

| Serviço | URL |
|---------|-----|
| Frontend | http://localhost:4200 |
| API | http://localhost:5000/api |
| Swagger | http://localhost:5000/api/docs |
| MySQL | localhost:3309 |
| Redis | localhost:6379 |

### Local (desenvolvimento)

```bash
# Backend
cd back
npm install --legacy-peer-deps
npx prisma generate
npx prisma migrate deploy
npm run prisma:seed
npm run start:dev

# Frontend (outra aba)
cd front
npm install --legacy-peer-deps
npm start
```

## Funcionalidades

- Autenticação (JWT local + refresh, Google OAuth, reset de senha)
- CRUD de projetos com kanban board
- Tasks com prioridade, tipo, labels, checklist, dependências
- Módulo de estudos (planos, tópicos, sessões)
- Comentários com markdown e code reviews
- Documentos (specs, planos, ADRs)
- Dashboard e métricas
- API REST completa para agentes de IA

## Estrutura

```
web-client/
├── back/                 # Backend NestJS
│   ├── src/
│   │   ├── modules/      # Módulos por domínio (auth, tasks, study, etc.)
│   │   ├── database/     # Prisma config
│   │   └── main.ts       # Bootstrap
│   ├── prisma/
│   │   ├── schema.prisma # Modelo de dados
│   │   └── migrations/   # Migrations versionadas
│   └── Dockerfile
├── front/                # Frontend Angular
│   ├── src/app/
│   │   ├── pages/        # Páginas (board, task-detail, studies, etc.)
│   │   ├── components/   # Componentes reutilizáveis
│   │   ├── services/     # Services HTTP
│   │   └── models/       # Interfaces TypeScript
│   ├── nginx.conf
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md             # Este arquivo
```

## API Endpoints

### Projetos
- `GET /api/projects` — Listar projetos
- `POST /api/projects` — Criar projeto
- `GET /api/projects/:id/board` — Board kanban

### Tarefas
- `GET /api/tasks` — Listar tarefas (filtros: projectId, status, priority, search)
- `POST /api/tasks` — Criar tarefa
- `GET /api/tasks/:code` — Detalhes da tarefa
- `PATCH /api/tasks/:code` — Atualizar tarefa
- `DELETE /api/tasks/:code` — Excluir tarefa
- `POST /api/tasks/:code/move` — Mover entre colunas

### Estudos
- `GET/POST /api/study/plans` — Planos de estudo
- `GET/PATCH/DELETE /api/study/plans/:id` — CRUD plano
- `GET/POST /api/study/plans/:id/topics` — Tópicos
- `POST /api/study/sessions` — Sessões de estudo
- `GET /api/study/stats` — Estatísticas

### Outros
- `GET/POST /api/comments` — Comentários
- `GET/POST /api/documents` — Documentos
- `GET/POST /api/labels` — Labels
- `GET /api/activity` — Log de atividade

## Variáveis de Ambiente

Copie `.env.example` para `.env` e ajuste conforme necessário:

```bash
cp .env.example .env
```

Variáveis principais:
- `DB_PASSWORD` — Senha do MySQL (default: mydbpassword)
- `DB_PORT` — Porta do MySQL no host (default: 3309)
- `API_PORT` — Porta da API (default: 5000)
- `FRONT_PORT` — Porta do frontend (default: 4200)

## Comandos Úteis

```bash
# Subir tudo
docker compose up --build

# Parar tudo
docker compose down

# Rebuildar apenas o backend
docker compose up --build api

# Ver logs
docker compose logs -f api
docker compose logs -f front

# Migration
cd back && npx prisma migrate dev --name <descricao>

# Seed
cd back && npm run prisma:seed
```
