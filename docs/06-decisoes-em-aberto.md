> 🇧🇷 [Versão em português](06-decisoes-em-aberto.ptbr.md)

# 06 — Open decisions

Choices worth aligning on before coding. Each has a **recommendation** to
unblock — change it if you disagree.

## D1 — Frontend: Angular or React? ✅ DECIDED: Angular

We will use **Angular** (`front/` from the template — Angular 20 standalone + NgRx +
CDK drag-drop). It is the main day-to-day stack (`wsi-front-angular`) and the CDK already
brings drag-and-drop ready for the kanban. Detailed architecture in
[doc 07 — Frontend Angular](07-frontend-angular.md).

The template's `front-react/` and `front-flutter/` will be removed from the project.

## D2 — Database: keep MySQL or go with Postgres?

The template is MySQL.

- **MySQL** — zero friction, already configured in the template/Docker.
- **Postgres** — better for `jsonb` (audit changes, scopes), partial indexes,
  and `LISTEN/NOTIFY` if we ever want real-time.

> **Recommendation:** **keep MySQL** in the MVP (full reuse of the template). Migrate to
> Postgres only if auditing/JSON becomes a burden. Prisma makes the switch easy later.

## D3 — Dedicated agent role (`AGENT`) or reuse `DEV`?

- Reuse **DEV** + restricted scopes on the key: fewer enums, simpler.
- Dedicated **AGENT** role: clearer auditing and UI ("this was an agent").

> **Recommendation:** start with **DEV + scopes**; introduce `AGENT` only if the
> visual/permission distinction becomes a real need.

## D4 — Kanban ordering: fractional rank (LexoRank) vs. integer `order`

- Integer `order`: simple, but reordering requires rewriting several rows.
- Fractional/lexicographic rank: moving = updating **one** row.

> **Recommendation:** **lexicographic rank** (`rank` string field). Cheap to move,
> scales well with agents working the board.

## D5 — Status: configurable columns vs. fixed enum

> **Recommendation:** **configurable columns** (status = `Column`). More flexible and
> already in the data model. No rigid status enum.

## D6 — Document versioning: `version` field vs. history table

- Incremental `version` on the doc itself: simple, keeps only the current one.
- `DocumentVersion` table: full history, allows diff/rollback.

> **Recommendation:** MVP with simple `version`; add full history in a
> later phase if there is demand for spec diff/rollback.

## D7 — Real-time on the board (websockets) now or later?

> **Recommendation:** **later.** In the MVP, refetch/polling is enough. Websockets (or
> Postgres LISTEN/NOTIFY) come in when there is real simultaneous collaboration.

## D8 — Product name ✅ DECIDED: Agentic Dev Maestro

Name decided: **Agentic Dev Maestro** (repo `agentic-dev-maestro`); short name
**Maestro**. Rationale in [doc 01](01-conceito-e-escopo.md#nome-decidido).

---

## Suggested next steps

1. ✅ Decided: **D1 (Angular)** and **D8 (Agentic Dev Maestro)**.
2. Clone the template into the project folder and build the **vertical slice** of
   [Phase 1](05-roadmap.md#fase-1--núcleo-de-tarefas-e-quadro): create and move a
   task via API with an API key, end to end.
3. Validate the **Maestro Loop** with a real agent (Claude Code) calling the API before
   investing in the rich UI.
