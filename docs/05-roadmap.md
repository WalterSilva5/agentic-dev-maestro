# 05 — Roadmap

Esforço em **homem-dia (hd)**, em faixas. **Não há alocação de pessoas nem
cronograma** — quem distribui o trabalho e define prazos é a liderança. As faixas
servem só para dimensionar o tamanho de cada bloco.

> Base: o template `fullstack-nestjs-angular` já entrega auth, usuários, papéis
> (USER/ADMIN/MANAGER), Prisma+MySQL, Bull/Redis, Swagger e Docker. As estimativas
> abaixo assumem esse ponto de partida.

---

## Fase 0 — Fundação multi-tenant · ~5–8 hd

Estender o template para o domínio de empresas e agentes.

- [ ] Modelos `Company` e `Membership` + migração Prisma — **1–2 hd**
- [ ] Adaptar papéis: novo enum `Role` (OWNER/MANAGER/TECH_LEAD/DEV/VIEWER) na Membership — **1 hd**
- [ ] Guard de contexto de empresa + filtro row-level por `companyId` — **1–2 hd**
- [ ] Modelo `ApiKey` + auth por `x-api-key` (hash, escopos, revogação) — **2 hd**
- [ ] Seed: empresa demo + owner + chave de agente — **0.5 hd**

## Fase 1 — Núcleo de tarefas e quadro · ~12–18 hd

O coração do produto.

- [ ] Modelos `Project`, `Board`, `Column`, `Task` (+ subtarefas) + migração — **2 hd**
- [ ] CRUD de projetos + criação de quadro com colunas padrão — **1.5 hd**
- [ ] CRUD de tarefas: criar, editar, atribuir, prioridade, estimativa (hd), tags — **2–3 hd**
- [ ] Endpoint `move` (mudar coluna/status + rank/ordenação) — **1 hd**
- [ ] Subtarefas (auto-relacional) — **1 hd**
- [ ] **Front:** tela de quadro kanban com drag-and-drop — **3–5 hd**
- [ ] **Front:** painel/modal de tarefa (detalhe, edição, subtarefas) — **2–3 hd**
- [ ] **Front:** lista de projetos + criação — **1.5 hd**

## Fase 2 — Docs e API de agente · ~8–12 hd

Onde o diferencial aparece.

- [ ] Modelo `Document` (markdown, versão) em projeto/tarefa + CRUD — **2 hd**
- [ ] **Front:** editor/visualizador markdown + export `.md` — **2–3 hd**
- [ ] `POST /tasks/bulk` (decompose: tarefas + subtarefas em transação) — **1.5 hd**
- [ ] Idempotência (`Idempotency-Key`) em criações — **1 hd**
- [ ] `ActivityLog` + gravação automática nas escritas (humano vs. agente) — **1.5 hd**
- [ ] **Front:** aba de atividade/auditoria na tarefa e no projeto — **1.5 hd**

**🎯 MVP funcional ao fim da Fase 2** (~25–38 hd acumulados): o loop completo
— briefing → doc → tarefas → quadro → execução por agente — roda de ponta a ponta.

## Fase 3 — Servidor MCP e integrações · ~6–10 hd

- [ ] Pacote do servidor MCP envolvendo a API — **3–4 hd**
- [ ] Tools MCP: `decompose`, `write_doc`, `list_tasks`, `move_task`, `comment` — **2–3 hd**
- [ ] Webhooks de mudança de status (fila Bull) — **1.5 hd**
- [ ] Notificações por e-mail (reaproveita fila do template) — **1 hd**

## Fase 4 — Visão e polish · ~6–10 hd

- [ ] Busca + filtros avançados (assignee, label, status, texto) — **2 hd**
- [ ] Etiquetas/labels por empresa — **1 hd**
- [ ] Dashboard de gerente (progresso por projeto/empresa) — **2–3 hd**
- [ ] Gestão de membros e API keys na UI — **2 hd**
- [ ] Convites de usuário para empresa — **1.5 hd**

---

## Resumo do esforço

| Fase | Foco | Esforço |
|---|---|---|
| 0 | Fundação multi-tenant | ~5–8 hd |
| 1 | Núcleo de tarefas e quadro | ~12–18 hd |
| 2 | Docs e API de agente | ~8–12 hd |
| **—** | **MVP funcional (0→2)** | **~25–38 hd** |
| 3 | MCP e integrações | ~6–10 hd |
| 4 | Visão e polish | ~6–10 hd |
| **—** | **Produto completo (0→4)** | **~37–58 hd** |

## Sugestão de fatiamento de entrega

1. **Vertical slice primeiro:** uma empresa, um projeto, um quadro, criar/mover uma
   tarefa via API com chave — prova o conceito ponta a ponta antes da UI rica.
2. **Depois** a UI de kanban, **depois** docs/bulk/auditoria, **por fim** MCP e polish.
