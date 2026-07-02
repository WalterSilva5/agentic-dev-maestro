> 🇬🇧 [English version](backend.md)

# Tarefas — Backend (NestJS + Prisma)

Base: template `fullstack-nestjs-angular` (auth, usuários, papéis, Prisma/MySQL,
Bull/Redis, Swagger já prontos). Esforço em homem-dia (hd).

---

## Fase 0 — Fundação multi-tenant

### B0.1 — Setup do projeto a partir do template · 0.5 hd
- [ ] Copiar `back/` do template para o projeto `maestro`
- [ ] Renomear app/pacote, ajustar `.env.example` (DB, JWT, REDIS)
- [ ] Subir com Docker (`docker compose up`) e validar `/api/docs` (Swagger)

### B0.2 — Modelos Company e Membership · 1.5 hd
- [ ] Adicionar `Company`, `Membership`, enum `Role` ao `schema.prisma`
- [ ] Relação `User ↔ Membership ↔ Company` (`@@unique([userId, companyId])`)
- [ ] Migração + `prisma generate`
- [ ] Módulos `companies` e `memberships` (CRUD básico)

### B0.3 — Guard de contexto multi-tenant · 1.5 hd
- [ ] Resolver `companyId` do JWT (`X-Company-Id`) ou da API key
- [ ] Carregar a `Membership` e expor papel no request context
- [ ] **Filtro row-level**: helper/decorator que injeta `companyId` em toda query
- [ ] Bloquear acesso cruzado entre empresas (teste de isolamento)

### B0.4 — Autenticação por API key · 2 hd
- [ ] Modelo `ApiKey` (hash, prefix, scopes, expiresAt, revokedAt) + migração
- [ ] Geração: cria chave, retorna o segredo **uma vez**, guarda só o hash
- [ ] Guard `x-api-key` → resolve `Membership` + `scopes`
- [ ] Endpoints: listar / criar / revogar (escopo `apikeys:manage`)
- [ ] Rate limit por chave + atualização de `lastUsedAt`

### B0.5 — Seed inicial · 0.5 hd
- [ ] Empresa demo + usuário OWNER + 1 API key de agente (papel DEV)

---

## Fase 1 — Núcleo de tarefas e quadro

### B1.1 — Projetos · 1.5 hd
- [ ] Modelo `Project` (`key`, `@@unique([companyId, key])`) + migração
- [ ] CRUD de projetos (escopo `projects:*`)
- [ ] Ao criar projeto, criar `Board` padrão + colunas padrão

### B1.2 — Quadro, colunas e ordenação · 1.5 hd
- [ ] Modelos `Board`, `Column` (order, wipLimit) + migração
- [ ] Endpoints: ler board completo, criar/renomear/reordenar coluna
- [ ] Estratégia de `rank` lexicográfico (helper de inserção/movimentação)

### B1.3 — Tarefas e subtarefas · 3 hd
- [ ] Modelo `Task` (number sequencial, parentId, estimateMd, priority, rank, **objective**, **acceptance**)
- [ ] CRUD de tarefa; geração do `number` → código `GAV-42`
- [ ] Aceitar `idOrCode` nas rotas (`/tasks/GAV-42`)
- [ ] Subtarefas (auto-relacional)
- [ ] `POST /tasks/:code/move` (muda coluna + rank) com validação de WIP

### B1.6 — Dependências e fluxo da tarefa (DAG) · 2.5 hd
> Feature do [doc 08](../08-fluxo-de-tarefas.md).
- [ ] Modelo `TaskDependency` (blocker → blocked) + migração; `@@unique`
- [ ] `POST /tasks/:code/dependencies` com **validação de ciclo** (DFS) + mesmo `companyId`
- [ ] `DELETE /tasks/:code/dependencies/:depId`
- [ ] `GET /tasks/:code/flow` → `{ nodes, edges }` com nós sintéticos **Objetivo** e **Aceite**
- [ ] Derivar estado **bloqueada** (blocker não concluído) + progresso (% subtarefas)
- [ ] `?format=mermaid` → emite `flowchart` para export na doc markdown
- [ ] No `POST /tasks/bulk`, resolver `dependsOn` (refs do lote) → cria arestas na transação

### B1.4 — Labels · 1 hd
- [ ] Modelo `Label` por empresa + relação N:N com `Task`
- [ ] Endpoints de label + aplicar/remover em tarefa

### B1.5 — Swagger + DTOs + validação · 1 hd
- [ ] DTOs com `class-validator` para tudo acima
- [ ] Tags Swagger organizadas por recurso; exemplos nos endpoints de agente

---

## Fase 2 — Docs e API de agente

### B2.1 — Documentos markdown · 2 hd
- [ ] Modelo `Document` (body markdown, type, version) ligado a Project/Task
- [ ] CRUD; incremento de `version` ao editar
- [ ] Endpoint de export (texto markdown puro)

### B2.2 — Bulk create (decompose) · 1.5 hd
- [ ] `POST /tasks/bulk` aceita array com subtarefas aninhadas
- [ ] Criação em **transação** (tudo ou nada)
- [ ] Retorna os códigos gerados (`GAV-1..n`)

### B2.3 — Idempotência · 1 hd
- [ ] Header `Idempotency-Key` em criações (docs e tarefas)
- [ ] Tabela/cache de chaves processadas (TTL) → reenvio não duplica

### B2.4 — Auditoria · 1.5 hd
- [ ] Modelo `ActivityLog` (actorUserId, viaApiKeyId, action, changes)
- [ ] Interceptor/serviço que registra toda escrita (humano vs. agente)
- [ ] Endpoint de leitura da atividade (por tarefa/projeto)

---

## Fase 3/4 — RBAC, integrações e polish

### B3.1 — RBAC declarativo · 1.5 hd
- [ ] Decorator `@RequireScope(...)` / `@RequireRole(...)`
- [ ] Guard que aplica **permissão efetiva = papel ∩ scopes** (ver matriz no doc 04)
- [ ] Testes da matriz de permissões por papel

### B3.2 — Webhooks e notificações · 2.5 hd
- [ ] Fila Bull: evento de mudança de status → dispara webhook(s) da empresa
- [ ] E-mail de notificação reusando a fila do template
- [ ] Config de webhooks por empresa (URL, secret HMAC)

### B4.1 — Busca e filtros · 2 hd
- [ ] `GET /tasks` com filtros (status, assignee, label, prioridade, texto)
- [ ] Paginação e ordenação

### B4.2 — Convites e gestão de membros · 1.5 hd
- [ ] Convidar usuário para empresa (por e-mail) + aceitar
- [ ] Mudar papel / remover membro (respeitando regras de OWNER)

---

## Checklist de qualidade (backend)

- [ ] Isolamento multi-tenant testado (nenhuma query sem `companyId`)
- [ ] API key: só hash no banco; segredo exibido 1x; revogação imediata funciona
- [ ] Toda escrita gera `ActivityLog` com ator correto
- [ ] Bulk + idempotência testados contra duplicação
- [ ] Matriz de permissões coberta por testes
- [ ] Swagger completo e atualizado (`/api/docs`)
- [ ] Migrations versionadas; seed reprodutível
