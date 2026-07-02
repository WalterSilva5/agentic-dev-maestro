> 🇧🇷 [Versão em português](README.ptbr.md)

# Web Client — Agentic Dev Maestro

Maestro web client. NestJS 8 backend + Angular 20 frontend, running via Docker.

## Stack

- **Backend**: NestJS 8 + Prisma 4.8 + MySQL 8 + Bull/Redis
- **Frontend**: Angular 20 (standalone) + Tailwind CSS + NgRx + Capacitor

## Quick Start

### Docker (recommended)

```bash
cp .env.example .env
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:4200 |
| API | http://localhost:5000/api |
| Swagger | http://localhost:5000/api/docs |
| MySQL | localhost:3309 |
| Redis | localhost:6379 |

### Local (development)

```bash
# Backend
cd back
npm install --legacy-peer-deps
npx prisma generate
npx prisma migrate deploy
npm run prisma:seed
npm run start:dev

# Frontend (another tab)
cd front
npm install --legacy-peer-deps
npm start
```

## Features

- Authentication (local JWT + refresh, Google OAuth, password reset)
- Project CRUD with kanban board
- Tasks with priority, type, labels, checklist, dependencies
- Study module (plans, topics, sessions)
- Comments with markdown and code reviews
- Documents (specs, plans, ADRs)
- Dashboard and metrics
- Complete REST API for AI agents

## Structure

```
web-client/
├── back/                 # NestJS backend
│   ├── src/
│   │   ├── modules/      # Domain modules (auth, tasks, study, etc.)
│   │   ├── database/     # Prisma config
│   │   └── main.ts       # Bootstrap
│   ├── prisma/
│   │   ├── schema.prisma # Data model
│   │   └── migrations/   # Versioned migrations
│   └── Dockerfile
├── front/                # Angular frontend
│   ├── src/app/
│   │   ├── pages/        # Pages (board, task-detail, studies, etc.)
│   │   ├── components/   # Reusable components
│   │   ├── services/     # HTTP services
│   │   └── models/       # TypeScript interfaces
│   ├── nginx.conf
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md             # This file
```

## API Endpoints

### Projects
- `GET /api/projects` — List projects
- `POST /api/projects` — Create project
- `GET /api/projects/:id/board` — Kanban board

### Tasks
- `GET /api/tasks` — List tasks (filters: projectId, status, priority, search)
- `POST /api/tasks` — Create task
- `GET /api/tasks/:code` — Task details
- `PATCH /api/tasks/:code` — Update task
- `DELETE /api/tasks/:code` — Delete task
- `POST /api/tasks/:code/move` — Move between columns

### Studies
- `GET/POST /api/study/plans` — Study plans
- `GET/PATCH/DELETE /api/study/plans/:id` — Plan CRUD
- `GET/POST /api/study/plans/:id/topics` — Topics
- `POST /api/study/sessions` — Study sessions
- `GET /api/study/stats` — Statistics

### Others
- `GET/POST /api/comments` — Comments
- `GET/POST /api/documents` — Documents
- `GET/POST /api/labels` — Labels
- `GET /api/activity` — Activity log

## Environment Variables

Copy `.env.example` to `.env` and adjust as needed:

```bash
cp .env.example .env
```

Main variables:
- `DB_PASSWORD` — MySQL password (default: mydbpassword)
- `DB_PORT` — MySQL port on the host (default: 3309)
- `API_PORT` — API port (default: 5000)
- `FRONT_PORT` — Frontend port (default: 4200)

## Useful Commands

```bash
# Bring everything up
docker compose up --build

# Bring everything down
docker compose down

# Rebuild only the backend
docker compose up --build api

# View logs
docker compose logs -f api
docker compose logs -f front

# Migration
cd back && npx prisma migrate dev --name <description>

# Seed
cd back && npm run prisma:seed
```
