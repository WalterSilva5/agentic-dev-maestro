# Checklist mestre — Definition of Done

Visão única do que precisa estar pronto. Estado em 2026-06-25.

> Convenção: `[ ]` a fazer · `[~]` parcial · `[x]` feito.

---

## 🚪 Gate 0 — Fundação multi-tenant ✅

- [x] Projeto a partir do template; `docker compose` sobe mysql/redis/api/front
- [x] `Company` + `Membership` + papéis (OWNER/MANAGER/TECH_LEAD/DEV/VIEWER)
- [x] Guard de contexto + **isolamento por `companyId`**
- [x] Autenticação por **API key** (hash sha256, escopos, expiração, revogação)
- [x] Seed: empresa demo + OWNER + API key de agente

## 🚪 Gate 1 — Núcleo de tarefas e quadro ✅

- [x] Projetos com `key` e board padrão automático (5 colunas)
- [x] Quadro com colunas configuráveis + `rank` lexicográfico
- [x] Tarefas com código (`DEMO-42`), prioridade, estimativa (hd), labels
- [x] Tarefas com **objetivo** e **critério de aceite**
- [x] Subtarefas (auto-relacional)
- [x] `move` (mudar coluna/status) — feito
- [x] **Fluxo da tarefa:** `TaskDependency` (DAG validado, anticiclo) + `GET /flow`
- [x] **Front:** kanban com drag-and-drop, update otimista + rollback
- [x] **Front:** detalhe de tarefa (objetivo, aceite, comentários; subtarefas via fluxo)
- [x] **Front:** aba de fluxo com nós por status + export Mermaid

## 🚪 Gate 2 — Docs e API de agente → MVP funcional ✅

- [x] `Document` markdown (versão) em projeto/tarefa + export
- [x] `POST /tasks/bulk` (decompose) em transação, com `dependsOn`
- [x] Idempotência (`Idempotency-Key`) sem duplicar
- [x] `ActivityLog` em toda escrita (humano vs. agente)
- [x] **Front:** editor/visualizador markdown (textarea) + aba de atividade

## 🚪 Gate 3 — MCP e integrações ✅

- [x] Servidor MCP (`mcp/`) com 11 tools
- [x] Webhooks de status (dispatch HMAC em `task.created/moved`)

## 🚪 Gate 4 — Visão e polish ✅

- [x] Busca + filtros no `GET /tasks`
- [x] Dashboard (progresso por projeto + atividade recente)
- [x] Gestão de membros e API keys na UI
- [x] Links de navegação (navbar) para as páginas do Maestro

## 🚪 Gate 5 — Modulo de Estudos ✅

- [x] Modelos SQLAlchemy: StudyPlan, StudyTopic, StudySession
- [x] Endpoints CRUD para planos, tópicos e sessões
- [x] Cálculo de progresso automático
- [x] GUI com lista de planos, detalhe com tópicos
- [x] Sidebar "Estudos" no local-client

## 🚪 Gate 6 — Edição/Deleção de Tarefas ✅

- [x] Backend: `PATCH /tasks/:code` (update), `DELETE /tasks/:code` (soft delete)
- [x] Backend: `PATCH /comments/:id` (update), `DELETE /comments/:id` (delete)
- [x] Backend: Filtro `parentId` no `GET /tasks`
- [x] Frontend: Cards clicáveis no board → abrem detalhes
- [x] Frontend: Formulário de edição inline na task detail
- [x] Frontend: Aba de subtarefas (criar/excluir, só título)
- [x] Frontend: Edição/deleção inline de comentários
- [x] Frontend: Seletor de coluna para mover tarefa
- [x] Frontend: Card de descrição destacado

## 🚪 Gate 7 — OpenCode Tools ✅

- [x] 12 ferramentas customizadas (`.opencode/tools/maestro.ts`)
- [x] 2 comandos: `/review` e `/decompose`
- [x] Skill de uso da plataforma
- [x] Config `opencode.jsonc`

## 🚪 Gate 8 — Reorganização ✅

- [x] Web client movido para `web-client/`
- [x] README geral + README do web client
- [x] CLAUDE.md atualizado com novos caminhos
- [x] Tema claro com melhor contraste (cards brancos, bordas visíveis)
- [x] Sidebar sem scroll desnecessário
- [x] Board view mostra lista de projetos quando nenhum selecionado

---

## Pendências conhecidas (próximos passos)

1. Timer real para sessões de estudo
2. Gamificação (streak, badges, XP)
3. Importação de roadmaps em markdown
4. Flashcards/revisão espaçada
5. Compartilhamento de planos como template
6. CI (lint + test + build) — não configurado
7. Testes automatizados (RBAC, isolamento)
