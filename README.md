# Agentic Dev Maestro

> *Maestro, para os íntimos.*

> **Da descrição à entrega.** Um workspace de tarefas onde humanos e agentes de IA
> trabalham lado a lado: você joga um briefing bruto, ele vira documentação
> estruturada + uma árvore de tarefas num quadro kanban, e os agentes (via API key)
> executam e mantêm o status sincronizado — com visibilidade total para devs, tech
> leads e gerentes.

O **Agentic Dev Maestro** é a evolução de um fluxo que já funciona hoje de forma manual: receber uma
tarefa/projeto, passar a descrição para um agente, otimizar a documentação, gerar
lista de tarefas/subtarefas/dicas e compartilhar os markdowns com o time. O produto
transforma esse fluxo num **sistema de registro** com API, quadros e papéis.

---

## O "Maestro Loop"

```
1. BRIEFING   → alguém joga uma descrição crua de tarefa/projeto
2. REFINO     → um agente transforma em doc estruturada (objetivo, escopo,
                contexto, critérios de aceite, riscos, dicas)
3. DECOMPOSE  → o agente quebra em tarefas → subtarefas, com estimativa
                em homem-dia, dependências e tags
4. QUADRO     → tudo cai num kanban com colunas/status configuráveis
5. EXECUÇÃO   → agentes pegam tarefas, mudam status, anexam docs/links de PR,
                registram progresso; humanos revisam
6. VISÃO      → gerentes e tech leads veem ao vivo; docs exportáveis em .md
```

Esse loop **é o produto** — a etapa de refino + decompose é o diferencial, não um
recurso secundário.

## Por que não só usar Jira / Linear / Trello?

| | Ferramentas tradicionais | Maestro |
|---|---|---|
| Agentes de IA | automação "bolada por cima" | **cidadãos de primeira classe** (API key por usuário, com escopos e auditoria) |
| Documentação | anexos / wiki separada | **markdown nativo e versionado** colado em projeto/tarefa, exportável |
| Spec → tarefas | manual | **pipeline embutido** (refino + decompose por agente) |
| Estimativa | story points / horas | **homem-dia**, sem alocar pessoas (staffing é decisão da liderança) |
| Integração com agentes | webhooks/plugins | **REST + servidor MCP** para qualquer agente conversar nativamente |

## Stack (reaproveita o template `fullstack-nestjs-angular`)

| Camada | Tecnologia |
|---|---|
| Backend | NestJS + Prisma (MySQL) + Bull/Redis + JWT/Passport + Swagger |
| Auth humano | JWT + refresh (já no template) |
| Auth agente | **API key** (`x-api-key`), com escopos e rate limit |
| Frontend | **Angular 20** (standalone + NgRx + CDK drag-drop) — kanban com drag-and-drop |
| Integração agente | **servidor MCP** envolvendo a API REST |
| Infra | Docker multi-stage, Nginx, MySQL, Redis |

O template já entrega: autenticação completa, CRUD de usuários, papéis, filas
assíncronas, config de app, health check e Swagger. O trabalho novo é **o domínio**:
empresas, membros, projetos, quadros, tarefas, docs, API keys e a API para agentes.

## Documentação

| Doc | Conteúdo |
|---|---|
| [01 — Conceito e escopo](docs/01-conceito-e-escopo.md) | problema, personas, diferenciais, escopo do MVP |
| [02 — Modelo de dados](docs/02-modelo-de-dados.md) | entidades, relacionamentos, esboço Prisma |
| [03 — API e agentes](docs/03-api-e-agentes.md) | endpoints, API keys, MCP, fluxos de agente |
| [04 — RBAC e multi-tenant](docs/04-rbac-e-multitenant.md) | papéis, matriz de permissões, isolamento por empresa |
| [05 — Roadmap](docs/05-roadmap.md) | fases, épicos, tarefas/subtarefas e esforço em homem-dia |
| [06 — Decisões em aberto](docs/06-decisoes-em-aberto.md) | escolhas pendentes (ADRs) |
| [07 — Frontend Angular](docs/07-frontend-angular.md) | arquitetura do front, estado, kanban com CDK |
| [08 — Fluxo de tarefas](docs/08-fluxo-de-tarefas.md) | tarefa como fluxograma: objetivo → subtarefas (dependências) → aceite |
| [Diagramas](docs/diagramas/) | fluxogramas em PlantUML (`.puml`) + SVG renderizado |
| [Tarefas e checklists](docs/tarefas/) | listas acionáveis por área (backend, frontend, infra, agentes) |
| [CHECKLIST.md](docs/CHECKLIST.md) | checklist mestre / definition of done |

## Status

🌱 **Brainstorming / planejamento.** Nada implementado ainda — esta pasta contém a
documentação de concepção. Nome definido: **Agentic Dev Maestro** (repo `agentic-dev-maestro`),
"Maestro" para o dia a dia.

## Licença

**Software proprietário** — todos os direitos reservados. Uso, cópia, modificação e
distribuição são proibidos sem permissão prévia por escrito. Ver [LICENSE](LICENSE).

> Nota: ao clonar o template `fullstack-nestjs-angular` (MIT) para dentro deste
> projeto, **substituir** o `LICENSE` do template por este.
