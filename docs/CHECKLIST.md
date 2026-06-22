# Checklist mestre — Definition of Done

Visão única do que precisa estar pronto. As listas detalhadas por área ficam em
[`tarefas/`](tarefas/). Marque aqui os **portões** (gates) de cada nível.

> Convenção: `[ ]` a fazer · `[~]` em andamento · `[x]` feito.

---

## 🚪 Gate 0 — Fundação multi-tenant

- [ ] Projeto criado a partir do template; `docker compose up` sobe tudo
- [ ] `Company` + `Membership` + papéis (OWNER/MANAGER/TECH_LEAD/DEV/VIEWER)
- [ ] Guard de contexto + **isolamento row-level por `companyId`** testado
- [ ] Autenticação por **API key** (hash, escopos, expiração, revogação)
- [ ] Seed: empresa demo + OWNER + API key de agente

## 🚪 Gate 1 — Núcleo de tarefas e quadro

- [ ] Projetos com `key` e board padrão automático
- [ ] Quadro com colunas configuráveis + `rank` lexicográfico
- [ ] Tarefas com código legível (`GAV-42`), prioridade, estimativa (hd), labels
- [ ] Tarefas com **objetivo** e **critério de aceite**
- [ ] Subtarefas (auto-relacional)
- [ ] `move` (mudar coluna/status) com WIP respeitado
- [ ] **Fluxo da tarefa:** `TaskDependency` (DAG validado) + `GET /flow` (nós/arestas)
- [ ] **Front:** kanban com CDK drag-drop, update otimista + rollback
- [ ] **Front:** detalhe de tarefa (objetivo, aceite, subtarefas, comentários)
- [ ] **Front:** aba de fluxo (ngx-graph) com nós por status + export Mermaid

## 🚪 Gate 2 — Docs e API de agente  → **MVP funcional**

- [ ] `Document` markdown (versão) em projeto/tarefa + export `.md`
- [ ] `POST /tasks/bulk` (decompose) em transação
- [ ] Idempotência (`Idempotency-Key`) sem duplicar
- [ ] `ActivityLog` em toda escrita (humano vs. agente)
- [ ] **Front:** editor/visualizador markdown + aba de atividade
- [ ] ✅ **Maestro Loop roda ponta a ponta** (briefing → doc → tarefas → quadro → execução por agente)

## 🚪 Gate 3 — MCP e integrações

- [ ] Servidor MCP com tools (`decompose`, `write_doc`, `list_tasks`, `move_task`, `comment`)
- [ ] Loop completo validado via MCP num agente real
- [ ] Webhooks de mudança de status + e-mail (fila Bull)

## 🚪 Gate 4 — Visão e polish

- [ ] Busca + filtros (status, assignee, label, texto)
- [ ] Dashboard do gerente (progresso por projeto/empresa)
- [ ] Gestão de membros e API keys na UI + convites

---

## ✅ Qualidade transversal (vale para todos os gates)

**Segurança**
- [ ] Nenhuma query de domínio sem filtro `companyId` (isolamento provado)
- [ ] API key só como hash; segredo exibido uma única vez; revogação imediata
- [ ] Permissão efetiva = papel ∩ escopos, coberta por testes
- [ ] `.env` nunca commitado; segredos fora do código

**Confiabilidade**
- [ ] Bulk + idempotência testados contra duplicação
- [ ] Migrations versionadas; seed idempotente
- [ ] CI verde (lint + test + build) como pré-requisito de merge

**Documentação**
- [ ] Swagger completo e atualizado (`/api/docs`)
- [ ] Diagramas (`docs/diagramas/`) regenerados após mudanças de modelo/fluxo
- [ ] README e docs refletem o estado real

---

## Critério de "MVP pronto"

O MVP está pronto quando os **Gates 0, 1 e 2** estão completos e o **Maestro Loop
roda de ponta a ponta** com um agente real criando doc + tarefas via API key e
movendo o status no quadro, com tudo auditado. Gates 3 e 4 são incrementos sobre
esse núcleo.
