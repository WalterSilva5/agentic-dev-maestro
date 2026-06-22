# Checklist mestre — Definition of Done

Visão única do que precisa estar pronto. As listas detalhadas por área ficam em
[`tarefas/`](tarefas/).

> Convenção: `[ ]` a fazer · `[~]` parcial · `[x]` feito.
> Estado em 2026-06-22 — backend Gates 0–4, app Angular e servidor MCP implementados
> e verificados (e2e de API + click-through no browser). Desvios/pendências sinalizados.

---

## 🚪 Gate 0 — Fundação multi-tenant ✅

- [x] Projeto a partir do template; `docker compose` sobe mysql/redis/api/front
- [x] `Company` + `Membership` + papéis (OWNER/MANAGER/TECH_LEAD/DEV/VIEWER)
- [x] Guard de contexto + **isolamento por `companyId`** (provado: 401 sem chave, sem vazamento)
- [x] Autenticação por **API key** (hash sha256, escopos, expiração, revogação)
- [x] Seed: empresa demo + OWNER + API key de agente (segredo impresso)

## 🚪 Gate 1 — Núcleo de tarefas e quadro ✅

- [x] Projetos com `key` e board padrão automático (5 colunas)
- [x] Quadro com colunas configuráveis + `rank` lexicográfico
- [x] Tarefas com código (`DEMO-42`), prioridade, estimativa (hd), labels
- [x] Tarefas com **objetivo** e **critério de aceite**
- [x] Subtarefas (auto-relacional)
- [~] `move` (mudar coluna/status) — feito; `wipLimit` existe no schema mas **ainda não é imposto**
- [x] **Fluxo da tarefa:** `TaskDependency` (DAG validado, anticiclo) + `GET /flow` (nós/arestas)
- [x] **Front:** kanban com drag-and-drop, update otimista + rollback — *nativo HTML5* (não CDK)
- [x] **Front:** detalhe de tarefa (objetivo, aceite, comentários; subtarefas via fluxo)
- [x] **Front:** aba de fluxo com nós por status + export Mermaid — *SVG próprio* (não ngx-graph)

## 🚪 Gate 2 — Docs e API de agente → MVP funcional ✅

- [x] `Document` markdown (versão) em projeto/tarefa + export
- [x] `POST /tasks/bulk` (decompose) em transação, com `dependsOn`
- [x] Idempotência (`Idempotency-Key`) sem duplicar (testado)
- [x] `ActivityLog` em toda escrita (humano vs. agente)
- [x] **Front:** editor/visualizador markdown (textarea) + aba de atividade
- [x] ✅ **Maestro Loop ponta a ponta** (verificado por e2e de API key e click-through no browser)

## 🚪 Gate 3 — MCP e integrações ✅ (com ressalvas)

- [x] Servidor MCP (`mcp/`) com 11 tools (decompose, write_doc, list/get/move task, flow, comment, …)
- [~] Loop via MCP: **build + handshake stdio verificados**; falta rodar conectado a um agente real
- [~] Webhooks de status (dispatch HMAC em `task.created/moved`) + **e-mail** (notificação no convite de membro; webhooks não usam a fila Bull)

## 🚪 Gate 4 — Visão e polish ✅ (com ressalvas)

- [x] Busca + filtros (status, assignee, label, texto) no `GET /tasks`
- [x] Dashboard (progresso por projeto + atividade recente)
- [~] Gestão de membros e API keys na UI — convite só adiciona **usuário já cadastrado** (sem convite por e-mail a não-usuário)
- [x] Links de navegação (navbar) para as páginas do Maestro

---

## ✅ Qualidade transversal

**Segurança**
- [x] Nenhuma query de domínio sem filtro `companyId` (isolamento provado)
- [x] API key só como hash; segredo exibido uma única vez; revogação imediata
- [~] Permissão efetiva por papel (`@RequireRole` no guard) — **sem testes automatizados** ainda
- [x] `.env` (e `config.json` de teste) nunca commitados

**Confiabilidade**
- [x] Bulk + idempotência testados contra duplicação
- [x] Migrations versionadas (`maestro_domain`, `maestro_fase2_4`); seed idempotente
- [ ] CI (lint + test + build) — **não configurado**

**Documentação**
- [x] Swagger completo (`/api/docs`)
- [~] Diagramas (`docs/diagramas/`) — conceito ok; pequenas divergências do schema final (ex.: `BoardColumn`, `taskSeq`)
- [x] README e docs refletem o estado real

---

## Pendências conhecidas (próximos passos)

1. Impor `wipLimit` no `move`.
2. Testes automatizados (RBAC, isolamento) + pipeline de CI.
3. Convite por e-mail a usuário ainda não cadastrado.
4. Validar o MCP conectado a um agente real (Claude Code).
5. Regenerar diagramas com o schema final.
