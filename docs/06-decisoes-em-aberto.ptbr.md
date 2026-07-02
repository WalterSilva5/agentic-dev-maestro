> 🇬🇧 [English version](06-decisoes-em-aberto.md)

# 06 — Decisões em aberto

Escolhas que valem alinhar antes de codar. Cada uma tem uma **recomendação** para
destravar — mude se discordar.

## D1 — Frontend: Angular ou React? ✅ DECIDIDO: Angular

Usaremos o **Angular** (`front/` do template — Angular 20 standalone + NgRx +
CDK drag-drop). É o stack principal do dia a dia (`wsi-front-angular`) e o CDK já
traz drag-and-drop pronto para o kanban. Arquitetura detalhada no
[doc 07 — Frontend Angular](07-frontend-angular.md).

O `front-react/` e o `front-flutter/` do template serão removidos do projeto.

## D2 — Banco: manter MySQL ou ir de Postgres?

O template é MySQL.

- **MySQL** — zero atrito, já configurado no template/Docker.
- **Postgres** — melhor para `jsonb` (changes do audit, scopes), índices parciais,
  e `LISTEN/NOTIFY` se um dia quiser real-time.

> **Recomendação:** **manter MySQL** no MVP (reuso total do template). Migrar para
> Postgres só se a auditoria/JSON pesar. Prisma facilita a troca depois.

## D3 — Papel dedicado para agente (`AGENT`) ou reusar `DEV`?

- Reusar **DEV** + escopos restritos na chave: menos enums, simples.
- Papel **AGENT** dedicado: auditoria e UI mais claras ("isso foi um agente").

> **Recomendação:** começar com **DEV + escopos**; introduzir `AGENT` só se a
> distinção visual/permissional virar necessidade real.

## D4 — Ordenação no kanban: rank fracionário (LexoRank) vs. `order` inteiro

- `order` inteiro: simples, mas reordenar exige reescrever várias linhas.
- Rank fracionário/lexicográfico: mover = atualizar **uma** linha.

> **Recomendação:** **rank lexicográfico** (campo `rank` string). Move barato,
> escala bem com agentes mexendo no quadro.

## D5 — Status: colunas configuráveis vs. enum fixo

> **Recomendação:** **colunas configuráveis** (status = `Column`). Mais flexível e
> já está no modelo de dados. Sem enum de status rígido.

## D6 — Versionamento de documentos: campo `version` vs. tabela de histórico

- `version` incremental no próprio doc: simples, guarda só a atual.
- Tabela `DocumentVersion`: histórico completo, permite diff/rollback.

> **Recomendação:** MVP com `version` simples; adicionar histórico completo numa
> fase posterior se houver demanda por diff/rollback de specs.

## D7 — Real-time no quadro (websockets) agora ou depois?

> **Recomendação:** **depois.** No MVP, refetch/polling basta. Websockets (ou
> Postgres LISTEN/NOTIFY) entram quando houver colaboração simultânea de verdade.

## D8 — Nome do produto ✅ DECIDIDO: Agentic Dev Maestro

Nome definido: **Agentic Dev Maestro** (repo `agentic-dev-maestro`); nome curto
**Maestro**. Justificativa em [doc 01](01-conceito-e-escopo.md#nome-decidido).

---

## Próximos passos sugeridos

1. ✅ Decididos: **D1 (Angular)** e **D8 (Agentic Dev Maestro)**.
2. Clonar o template para a pasta do projeto e fazer o **vertical slice** da
   [Fase 1](05-roadmap.md#fase-1--núcleo-de-tarefas-e-quadro): criar e mover uma
   tarefa via API com API key, ponta a ponta.
3. Validar o **Maestro Loop** com um agente real (Claude Code) chamando a API antes
   de investir na UI rica.
