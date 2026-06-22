# 01 — Conceito e escopo

## O problema

Hoje o fluxo de trabalho com agentes é:

1. Recebo uma tarefa/projeto (descrição crua, às vezes vaga).
2. Passo a descrição para um agente.
3. Juntos otimizamos a documentação, geramos lista de tarefas/subtarefas/dicas.
4. Os markdowns resultantes vão para outros devs e gerentes, dando visão do projeto.

Isso **funciona**, mas os artefatos ficam soltos (arquivos `.md` espalhados), sem
estado (o que está em andamento? quem fez o quê?), sem padronização e sem um lugar
único onde humanos e agentes compartilham a verdade. Não dá para ver progresso, nem
auditar o que um agente alterou.

## A solução

Uma aplicação **backend + frontend** que vira o sistema de registro desse fluxo:

- O agente acessa a **API** para criar tarefas, subtarefas e documentação.
- O agente **muda o status** das tarefas seguindo um **quadro kanban** configurável.
- A documentação otimizada vive **colada** ao projeto/tarefa (markdown, versionada,
  exportável) — o mesmo artefato que hoje é enviado para devs e gerentes.
- Tudo é **multi-empresa**: usuários se vinculam a empresas e são gerenciados pelos
  responsáveis dela.
- Agentes agem via **API key vinculada a um usuário**, herdando suas permissões e
  deixando rastro de auditoria (humano vs. agente).

## Personas

| Persona | Usa o Maestro para |
|---|---|
| **Dev** | ver suas tarefas, mover no quadro, ler a doc/dicas, comentar, abrir PRs ligados |
| **Tech Lead** | revisar, aprovar, ajustar decomposição, garantir qualidade técnica |
| **Manager** | visão de progresso por projeto/empresa, sem entrar no detalhe técnico |
| **Agente de IA** | refinar briefings em docs, decompor em tarefas/subtarefas, mover status, registrar progresso — tudo via API key |

## Diferenciais (o "porquê construir")

1. **Agente como cidadão de primeira classe** — não é integração colada por cima:
   o agente tem identidade (API key), escopos de permissão e auditoria.
2. **Pipeline spec → tarefas embutido** — refino + decompose é a feature central.
3. **Docs markdown nativas e exportáveis** — preserva o fluxo atual (mandar `.md`
   para o time), mas com estado e versão.
4. **Esforço em homem-dia, sem alocação** — estimativas em homem-dia; quem aloca
   pessoas e define cronograma é a liderança. O Maestro não escala equipe.
5. **Servidor MCP** — qualquer agente (Claude Code, etc.) conversa nativamente com
   os quadros via MCP, além do REST.

## Escopo do MVP (o que entra)

- Empresas + vínculo de usuários (membros) + papéis.
- Projetos dentro de empresas.
- Quadros kanban com colunas/status configuráveis.
- Tarefas e subtarefas (mover, atribuir, priorizar, estimar em homem-dia, tags).
- Documentos markdown em projeto/tarefa.
- API key por usuário (com escopos) para agentes.
- API REST com Swagger + endpoints amigáveis a agente (bulk create, idempotência).
- Log de auditoria (quem/qual agente fez o quê).

## Fora do escopo (por enquanto)

- Cronograma/Gantt e **alocação de pessoas** (decisão da liderança, não da ferramenta).
- Time tracking / apontamento de horas.
- Sprints/cycles formais (pode entrar depois como visão opcional).
- Faturamento/billing.
- Real-time colaborativo (websockets) — fica para uma fase posterior.

## Nome (decidido)

**Agentic Dev Maestro** — repo `agentic-dev-maestro`.

- **Agentic** — os agentes de IA agem com autonomia (não é automação colada).
- **Dev** — o domínio é trabalho de desenvolvimento (tarefas, docs, quadro).
- **Maestro** — orquestra o time misto (humanos + agentes) em torno do trabalho.

No dia a dia e na documentação, o nome curto é **Maestro** (daí "Maestro Loop",
"API Maestro" etc.).
