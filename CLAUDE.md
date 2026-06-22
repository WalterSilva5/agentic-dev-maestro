# Fullstack Template (NestJS + Angular/React/Flutter) — Guia para Agentes de IA

## Visão Geral

Template fullstack genérico (sem regra de negócio de domínio). Monorepo com backend e frontend no mesmo repositório:

- **Backend**: `back/` — NestJS 8 + Prisma 4.8 + MySQL 8 + Bull/Redis
- **Frontend (Angular)**: `front/` — Angular 20 (standalone) + Tailwind/Bootstrap + NgRx + Capacitor
- **Frontend (React)**: `front-react/` — React 19 + Vite 6 + Redux Toolkit + React Router 7 + Tailwind/daisyUI + Capacitor
- **Frontend (Flutter)**: `front-flutter/` — Flutter 3.44 / Dart 3.12 + Riverpod + go_router + dio + flutter_secure_storage (web + Android + iOS)

> Os três frontends têm **paridade de funcionalidades** e consomem a mesma API. Ao alterar um contrato de dados, mantenha todos sincronizados (ou remova os que não for usar). Cada um tem seu guia específico: `front-react/CLAUDE.md` e `front-flutter/CLAUDE.md`.

Funcionalidades prontas: autenticação (JWT local + refresh, Google OAuth, reset de senha), usuários, créditos, configuração de app, fila assíncrona de exemplo (e-mail) e health check.

---

## Regra Fundamental: Backend e Frontend Devem Estar Sincronizados

**Toda alteração em um lado DEVE ser refletida no outro.**

**Checklist para qualquer mudança de dados:**

1. `back/prisma/schema.prisma` — adicionar/alterar campo
2. `cd back && npx prisma migrate dev --name <descricao>` — cria a migration e regenera o client
3. DTOs em `back/src/modules/<modulo>/dto/` — atualizar validação (class-validator)
4. Repository em `back/src/modules/<modulo>/` — atualizar queries (controllers nunca acessam Prisma direto)
5. Service e Controller do módulo — atualizar lógica/endpoints
6. Frontend type/model — Angular: `front/src/app/models/`; React: `front-react/src/types/index.ts`; Flutter: `front-flutter/lib/models/models.dart`
7. Frontend service/API — Angular: `front/src/app/services/`; React: `front-react/src/api/`; Flutter: `front-flutter/lib/features/*/<recurso>_api.dart`
8. Frontend templates/páginas — exibir/editar o novo campo nos frontends que você mantiver

---

## Arquitetura do Backend

### Stack

- **NestJS 8** com módulos por domínio
- **Prisma 4.8** como ORM (MySQL 8)
- **Bull + Redis** para filas de jobs assíncronos
- **JWT + Passport** (local + refresh + Google OAuth)
- **Nodemailer** para envio de e-mail (via fila Bull)
- **Swagger** em `/api/docs`

### Estrutura de Diretórios

```text
back/src/
├── modules/
│   ├── auth/             # JWT (local + refresh), Google OAuth, reset de senha
│   ├── user/             # CRUD e perfil de usuário
│   ├── credit-account/   # Saldo de créditos por usuário
│   ├── credit-transaction/ # Histórico de movimentações
│   ├── email/            # Fila Bull de exemplo (reset de senha)
│   ├── app-config/       # Configurações chave/valor
│   ├── health/           # Health check
│   └── base/             # Service/controller base (CRUD + paginação)
├── database/             # Configuração Prisma
├── decorators/           # Decorators customizados (ex: @unprotected)
├── enums/                # Role, Gender, TransactionType
├── filters/              # Exception filters
└── main.ts               # Bootstrap (prefixo /api, porta 5000, Swagger)
```

### Padrão de Módulo

`auth` é o módulo de referência: controller fino, service com a lógica, repository encapsulando Prisma, DTOs com class-validator. O módulo `base` oferece CRUD genérico com paginação para reaproveitar em novos módulos.

### Autenticação

- Guard JWT global via `APP_GUARD`. Rotas públicas usam o decorator `@unprotected()`.
- Access + refresh token (`AT_SECRET` / `RT_SECRET`).
- Google OAuth: rota de callback `GET /api/auth/accounts/google/redirect` (configure `GOOGLE_CALLBACK_URL`).
- Reset de senha: enfileira job na fila `email` (Bull/Redis), processado em `email.processor.ts`.

### Banco de Dados

- MySQL via Docker (porta 3309 no host por padrão).
- **Migrations são reais e versionadas** em `back/prisma/migrations/` (`0_init` cria todas as tabelas).
- Aplicar migrations: `npx prisma migrate deploy` (produção) ou `npx prisma migrate dev` (desenvolvimento).
- Seed: `npm run prisma:seed` (cria `admin@template.com` / `Admin@123` e `user@template.com` / `User@123`).
- No Docker, migrations + seed rodam automaticamente via `back/docker-entrypoint.sh`.

---

## Arquitetura do Frontend

Há três frontends com paridade. O guia detalhado de cada um está no respectivo `CLAUDE.md` (`front/CLAUDE.md`, `front-react/CLAUDE.md`, `front-flutter/CLAUDE.md`).

### Frontend Angular (`front/`)

- **Angular 20** com standalone components
- **Tailwind CSS** + **Bootstrap 5** para estilos
- **NgRx** para state management (auth)
- **SweetAlert2** para modais/feedback (`Swal.fire()` direto)
- **Capacitor** para empacotamento PWA / mobile

```text
front/src/app/
├── pages/        # auth, home, user, credit, settings, not-found
├── components/   # Componentes reutilizáveis (navbar, mobile-bottom-nav, etc.)
├── services/     # Services HTTP e utilitários
├── models/       # Interfaces TypeScript
├── state/        # NgRx store (auth, roles)
├── routes/       # Rotas
└── modules/      # data-service (base com auth headers) + interceptors (JWT)
```

### Frontend React (`front-react/`)

- **React 19 + Vite 6** (SPA)
- **Redux Toolkit + React Redux** para state management (auth)
- **React Router 7** para rotas + guards (`ProtectedRoute`, `RoleRoute`)
- **axios** com refresh single-flight em 401 (`src/api/client.ts`)
- **Tailwind CSS + daisyUI**, **SweetAlert2**, **Capacitor**

```text
front-react/src/
├── api/          # client axios + módulos por recurso
├── components/   # Layout, Navbar, ProtectedRoute, RoleRoute
├── config/       # loadConfig() — config.json em runtime
├── lib/          # alerts (SweetAlert2), capacitor
├── pages/        # auth/, user/, Home, Settings, NotFound
├── routes/       # paths.ts
├── store/        # Redux Toolkit (store, authSlice, tokenStore, hooks)
└── types/        # interfaces TypeScript
```

### Frontend Flutter (`front-flutter/`)

- **Flutter 3.44 / Dart 3.12** (web + Android + iOS)
- **Riverpod** para estado (config, token storage, auth `NotifierProvider`)
- **go_router** para rotas + guards (auth e role) via `refreshListenable`
- **dio** com refresh single-flight em 401 (`lib/core/api_client.dart`)
- **flutter_secure_storage** para tokens (cache em memória p/ leitura síncrona no interceptor)

```text
front-flutter/lib/
├── config/        # app_config.dart (configProvider), config_service.dart
├── core/          # api_client.dart (Dio+refresh), token_storage.dart, api_exception.dart
├── models/        # models.dart — User, CreditAccount, AuthTokens, Paginated<T>
├── features/      # auth/, home/, user/, credits/, transactions/, settings/, shell/
├── routing/       # paths.dart, app_router.dart (go_router + guards)
├── shared/        # theme.dart, alerts.dart, external_link.dart
├── app.dart       # MaterialApp.router
└── main.dart      # carrega config + storage, ProviderScope overrides, runApp
```

### Configuração em Runtime

Os frontends carregam a config em runtime (não em build):

- `apiUrl` — URL da API (default: `http://localhost:5000/api`)
- `app` — nome, versão, tema, deep link host
- Angular: `front/public/config.example.json`. React: `front-react/public/config.json`. Flutter: `front-flutter/assets/config.json` (empacotado) + override web em `front-flutter/web/config.json`.

---

## Convenções de Desenvolvimento

### Geral

- Commits e nomes de branches em português
- Código em inglês (variáveis, classes); textos da UI em português brasileiro
- Sem emojis no código, salvo se pedido
- **Nunca** commitar `.env` real — apenas `.env.example`

### Backend

- Um módulo NestJS por domínio (controller + service + repository + DTOs)
- Repository pattern — controllers nunca acessam Prisma diretamente
- DTOs com class-validator
- Erros via exceptions do NestJS (NotFoundException, ForbiddenException, etc.)

### Frontend

- Standalone components (sem NgModules)
- Services injetáveis para HTTP
- NgRx para estado global (auth)
- SweetAlert2 para feedback ao usuário
- Tailwind para estilos utilitários, SCSS para animações/media queries

---

## Comandos Úteis

### Subir tudo (Docker)

```bash
cp back/.env.example back/.env
docker compose up --build
# front Angular :4200 · front React :4300 · front Flutter :4400 · api :5000/api · swagger :5000/api/docs
```

### Backend

```bash
cd back
npm install --legacy-peer-deps
npx prisma generate
npx prisma migrate deploy     # aplicar migrations
npm run prisma:seed           # usuários iniciais
npm run start:dev             # http://localhost:5000
npm run build                 # build de produção (dist/main.js)
npx tsc --noEmit              # checar tipos
```

### Frontend (Angular)

```bash
cd front
npm install --legacy-peer-deps
npm start                     # ng serve — http://localhost:4200
npm run build                 # ng build
```

### Frontend (React)

```bash
cd front-react
npm install --legacy-peer-deps
npm run dev                   # vite — http://localhost:4200 (Docker: :4300)
npm run build                 # tsc --noEmit && vite build
```

### Frontend (Flutter)

```bash
cd front-flutter
flutter pub get
flutter run -d chrome --web-port 4400   # web (Docker: :4400)
flutter analyze               # lint/análise estática
flutter test                  # testes unitários
flutter build web --release   # build de produção (build/web/)
```

> Os installs usam `--legacy-peer-deps` por conflitos de peer-deps nos toolchains do NestJS 8, Angular 20 e React 19.

---

## Troubleshooting

### `npm install` falha com erro de peer dependency

Use `npm install --legacy-peer-deps` (NestJS 8 / Angular 20 têm conflitos de peer-deps esperados).

### Tabelas não existem / erro de conexão Prisma

Rode `npx prisma migrate deploy` com o MySQL no ar. No Docker isso é automático no boot da API.

### Fila travada / e-mail não envia

A fila Bull precisa de Redis no ar. Verifique `REDIS_HOST`/`REDIS_PORT` e o serviço `redis` no compose. O envio de e-mail exige `EMAIL_USER`/`EMAIL_PASSWORD`.

### Google OAuth não funciona

Confira `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` e `GOOGLE_CALLBACK_URL` (deve apontar para `/api/auth/accounts/google/redirect`).
