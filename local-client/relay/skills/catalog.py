SKILLS = [
    {
        "id": "relay-run",
        "name": "Run Relay Local",
        "category": "setup",
        "description": "Iniciar a aplicacao desktop (GUI + API)",
        "tags": ["setup", "launch"],
        "filename": "relay-run",
        "content": """---
description: Run the Relay Local desktop app (GUI + API)
---

# Run Relay Local

```bash
cd /home/wsi/repositorios/github/relay
source .venv/bin/activate
python -m relay
```

API fica disponivel em `http://127.0.0.1:9777/api`.

Para testar a API:
```bash
curl http://127.0.0.1:9777/api/health
```
""",
    },
    {
        "id": "relay-api-agent",
        "name": "API Agent Usage",
        "category": "agent",
        "description": "Interagir com a API REST como agente de IA",
        "tags": ["api", "agent", "rest"],
        "filename": "relay-api-agent",
        "content": """---
description: Interact with Relay Local API as an AI agent
---

# Agent API Usage

Base: `http://127.0.0.1:9777/api`

## Fluxo tipico de um agente

### 1. Verificar conexao
```bash
curl http://127.0.0.1:9777/api/health
```

### 2. Listar/criar projeto
```bash
curl http://127.0.0.1:9777/api/projects
curl -X POST http://127.0.0.1:9777/api/projects -H 'Content-Type: application/json' -d '{"name":"Meu Projeto","key":"MP"}'
# previsao de entrega do projeto (contagem regressiva nas metricas)
curl -X PATCH http://127.0.0.1:9777/api/projects/1 -H 'Content-Type: application/json' -d '{"targetDate":"2026-12-31"}'
```

### 3. Ver board
```bash
curl http://127.0.0.1:9777/api/projects/1/board
```

### 4. Criar tarefa
```bash
curl -X POST http://127.0.0.1:9777/api/tasks -H 'Content-Type: application/json' \\
  -d '{"projectId":1,"title":"Implementar login","type":"FEATURE","priority":"HIGH"}'
```

### 5. Atualizar tarefa
```bash
curl -X PATCH http://127.0.0.1:9777/api/tasks/MP-1 -H 'Content-Type: application/json' \\
  -d '{"description":"Descricao detalhada","objective":"Objetivo claro"}'
```

### 6. Mover tarefa (mudar coluna)
```bash
curl -X POST http://127.0.0.1:9777/api/tasks/MP-1/move -H 'Content-Type: application/json' \\
  -d '{"columnId":3}'
```

### 7. Adicionar comentario (log de progresso)
```bash
curl -X POST http://127.0.0.1:9777/api/comments -H 'Content-Type: application/json' \\
  -d '{"taskId":1,"body":"Implementacao concluida","type":"COMMIT_REF"}'
```

### 8. Contexto completo da tarefa
```bash
curl http://127.0.0.1:9777/api/tasks/MP-1/context
```

### 9. Metricas
```bash
curl http://127.0.0.1:9777/api/projects/metrics
```

## Tipos de tarefa
FEATURE, BUG, TECH_DEBT, IMPROVEMENT, CHORE

## Prioridades
LOW, MEDIUM, HIGH, URGENT

## Tipos de comentario
COMMENT, CODE_REVIEW, COMMIT_REF, DEPLOY_LOG

## Modelo simplificado do card

Um card tem: titulo, texto (description), responsavel (assignee, texto livre),
data alvo (dueDate ISO), sprint (sprintId), coluna (columnId), tags, epicos,
cards vinculados e comentarios. Sem anexos, checklist ou subtarefas na UI
(a API ainda aceita objective/acceptance/estimateMd/type/parentId por
compatibilidade, mas novos fluxos nao devem usa-los).

## Epicos

```bash
# Listar/criar
curl http://127.0.0.1:9777/api/projects/1/epics
curl -X POST http://127.0.0.1:9777/api/projects/1/epics -H 'Content-Type: application/json' -d '{"name":"Cashier"}'
# Vincular/desvincular card
curl -X POST http://127.0.0.1:9777/api/epics/1/tasks/2
curl -X DELETE http://127.0.0.1:9777/api/epics/1/tasks/2
```

## Goals (objetivos com progresso)

```bash
# Criar: entregar cards com tag/épico/sprint ate a data
curl -X POST http://127.0.0.1:9777/api/projects/1/goals -H 'Content-Type: application/json' \\
  -d '{"name":"Entregar onda-1","dueDate":"2026-12-31","tag":"onda-1"}'
# Progresso (total/done/pct/daysLeft) vem embutido no GET e no POST
curl http://127.0.0.1:9777/api/goals/1
curl -X PATCH http://127.0.0.1:9777/api/goals/1 -H 'Content-Type: application/json' -d '{"tag":"onda-2"}'
```

## Responsaveis (membros do projeto)

```bash
# Listar (com metricas: total/developed/developedPct/done/pct/overdue) e adicionar
curl http://127.0.0.1:9777/api/projects/1/members
curl -X POST http://127.0.0.1:9777/api/projects/1/members -H 'Content-Type: application/json' -d '{"name":"Walter"}'
# Atribuir card pelo nome (cria o membro se nao existir)
curl -X PATCH http://127.0.0.1:9777/api/tasks/KEY-1 -H 'Content-Type: application/json' -d '{"assignee":"Walter"}'
```

## Metricas por dimensao (modulo != sprint != tag)

Nem toda label e modulo: na mesma lista convivem modulo (`cashier`), submodulo
(`cfg-e1`), sprint (`sprint-2`), plataforma (`vm`) e natureza (`fundacao`).

```bash
curl -s http://127.0.0.1:9777/api/projects/1/metrics/dimensions | jq '{
  cards, local, with_module, unlabeled,
  modulos: [.modules[] | {label, done, total, pct, submodules}],
  sprints: .sprints, plataformas: .platforms, natureza: .process
}'
```

- `modules[]` — modulo de entrega com `submodules[]` (nomes da taxonomia: "E1 · loja")
  - `developed`/`developedPct` = **dev concluido** (card em Dev Box ou depois)
  - `done`/`pct` = **aceito** (coluna de conclusao). Use `developed` para
    progresso do modulo; `done` conta so o que ja passou pelo aceite
  - so aparecem grupos com cards; sem metas nem contagens planejadas
- `developmentColumn` — coluna usada como "dev concluido" (normalmente `Dev Box`)
- `sprints[]` / `platforms[]` / `process[]` — dimensoes separadas (nao entram no % por modulo)
- `local` — tarefas locais excluidas do calculo

## Quem chegou em cada estagio (cumulativo)

Duas leituras, sem inventar historico:
- `current` = quantos cards estao NA coluna agora
- `reached`/`atOrAfter` = quantos estao nessa coluna OU adiante no fluxo
Fluxo: Doing -> Dev Review -> Dev Box (dev concluido, aguardando teste) -> In Test -> Done.

```bash
curl -s "http://127.0.0.1:9777/api/projects/1/metrics/stages?stage=dev-box" | jq '{
  total, local,
  estagios: [.stages[] | {name, reached, pct, current}],
  dev_box: .selected
}'
```

- `current` = esta agora; `reached`/`atOrAfter` = neste estagio ou depois
- nao e historico de passagem: card importado nao tem movimentacao registrada
- ordem: `Doing -> Dev Review -> Dev Box -> In Test -> ... -> Done`
- `breakdown[estagio][]` = corte por modulo, **soma 100%** (um card por grupo;
  card sem modulo vira `sem-modulo`)
- `stage=` devolve `selected` com `groups` do estagio
- "chegou" = ordem das colunas + `activity_log` (`moved`, "Origem -> Destino")

## Tarefas locais (nao sincronizam com o board externo)

```bash
curl -s -X POST http://127.0.0.1:9777/api/tasks -H 'Content-Type: application/json' \\
  -d '{"projectId":1,"columnId":5,"title":"revisar o que o dev fez hoje","type":"CHORE","isLocal":true}' \\
  | jq '{code, title, isLocal}'
```

- `isLocal: true` -> o card existe so no Relay; o sync do board externo nao
  cria, nao atualiza, nao apaga e nao sobrescreve numero igual
- `isLocal: false` (padrao) -> card espelhado do board externo
- `PATCH /api/tasks/{code}` com `{"isLocal": true|false}` converte
- **Nao entra no progresso** (% concluido, WIP, por coluna/responsavel/epico/
  modulo/estagio, goals); as respostas trazem `local: N`
- **Gera alerta de prazo**: vencidas, paradas 14d+ e "vence em 7 dias"

## Reunioes (gravacoes do desktop)

Mesmas gravacoes do app desktop, disponiveis tambem na web (`/reunioes`).

```bash
curl -s "http://127.0.0.1:9777/api/recordings?archived=all&q=migracao" | jq '.[] | {id,title,createdAt,hasSummary}'
curl -s "http://127.0.0.1:9777/api/recordings/1" | jq '{title, sections, transcript}'
curl -s -X PATCH "http://127.0.0.1:9777/api/recordings/1" -H 'Content-Type: application/json' \\
  -d '{"title":"Daily 08/11","tags":["daily"]}'
curl -s -X POST "http://127.0.0.1:9777/api/recordings/1/archive" -H 'Content-Type: application/json' -d '{"archived":true}'
curl -s -o reuniao.md "http://127.0.0.1:9777/api/recordings/1/export?format=md"   # md | txt | json
```

- `sections` = plano, dicas, acoes, decisoes e perguntas do assistente ao vivo
- export `md`: usa o resumo salvo ou monta a partir das secoes + transcricao
- `DELETE /api/recordings/{id}` remove; `GET /api/recordings/{id}/audio` serve o audio

## Backup do banco (quem copia e a API, nao o cliente)

```bash
# backup do workspace ativo (grava no servidor, em ~/relay-backups)
curl -s -X POST http://127.0.0.1:9777/api/backup | jq
# todos os workspaces
curl -s -X POST "http://127.0.0.1:9777/api/backup?all=1" | jq '.backups[] | {workspace, file, bytes}'
# listar os ultimos backups
curl -s http://127.0.0.1:9777/api/backup | jq '.dir, .backups[0]'
# baixar uma copia (o arquivo vem da pasta de backup do servidor)
curl -s -o copia.db "http://127.0.0.1:9777/api/backup/relay-gav-20261108-180558.db"
```

- destino: `~/relay-backups/relay-<workspace>-<AAAAMMDD-HHMMSS>.db`
  (configuravel em `settings.backup_dir` do `config.json`)
- a copia usa a API de backup do SQLite (instantaneo consistente, mesmo com o
  banco em uso) — o front so chama `POST /api/backup`
- `GET /api/backup/{arquivo}` valida o nome e so serve arquivo da pasta
""",
    },
    {
        "id": "relay-task-workflow",
        "name": "Task Workflow",
        "category": "workflow",
        "description": "Fluxo completo de trabalho com tarefas: pegar task, implementar, mover, documentar",
        "tags": ["workflow", "task", "development"],
        "filename": "relay-task-workflow",
        "content": """---
description: Complete task workflow - pick, implement, move, document
---

# Task Workflow

Fluxo padrao para trabalhar com uma tarefa no Relay Local.

## REGRAS FUNDAMENTAIS

### NUNCA fazer commits ou pushs sem autorizacao explicita

O agente **NUNCA** deve executar `git commit`, `git push`, ou qualquer
operacao de versionamento por conta propria. Commits e pushs so devem
ser feitos quando o desenvolvedor **explicitamente** pedir.

O agente e um auxiliar do desenvolvedor. Seu papel e:
1. **Auxiliar** na implementacao do codigo da tarefa
2. **Documentar** o que foi feito (comentarios, code review, docs)
3. **Criar tarefa de revisao** para o desenvolvedor validar as alteracoes
4. **Informar o desenvolvedor** sobre o estado e proximo passo
5. **Aguardar** a decisao do dev sobre commit/push

Ao terminar uma implementacao, o agente DEVE:
- Criar o code review como comentario na tarefa
- Criar uma TAREFA DE REVISAO para o desenvolvedor (ver passo 7)
- Informar ao dev: quais arquivos foram alterados, o que testar
- Perguntar ao dev se deseja fazer commit e push

### Respeitar flag "Requer desenvolvedor"

Antes de pegar qualquer tarefa, verifique o campo `requiresHuman`.
Tarefas com `"requiresHuman": true` devem ser feitas por um desenvolvedor
humano e NAO por agentes de IA. **Pule essas tarefas silenciosamente.**

## 1. Buscar proxima tarefa disponivel

```bash
# Listar tarefas no backlog ou "A fazer"
# IMPORTANTE: filtrar tarefas que NAO requerem humano
curl -s http://127.0.0.1:9777/api/tasks?status=Backlog | jq '[.[] | select(.requiresHuman != true)][0]'
curl -s http://127.0.0.1:9777/api/tasks?status=A+fazer | jq '[.[] | select(.requiresHuman != true)][0]'
```

## 2. Obter contexto completo

```bash
curl -s http://127.0.0.1:9777/api/tasks/{CODE}/context | jq .
```

O contexto inclui: tarefa, comentarios, documentos e atividade.

## 3. Mover para "Fazendo"

```bash
# Primeiro, descubra o ID da coluna "Fazendo"
curl -s http://127.0.0.1:9777/api/projects/{PROJECT_ID}/board | jq '.columns[] | select(.name=="Fazendo") | .id'

# Mover
curl -X POST http://127.0.0.1:9777/api/tasks/{CODE}/move \\
  -H 'Content-Type: application/json' \\
  -d '{"columnId": COLUMN_ID}'
```

## 4. Implementar e documentar progresso

Durante a implementacao, registre progresso via comentarios:

```bash
curl -X POST http://127.0.0.1:9777/api/comments \\
  -H 'Content-Type: application/json' \\
  -d '{"taskId":ID,"body":"Progresso: implementado modulo X","type":"COMMENT"}'
```

Tipos de comentario:
- `COMMENT` — comentario geral / progresso
- `CODE_REVIEW` — revisao de codigo (obrigatorio antes de Revisao)
- `COMMIT_REF` — referencia a commit (somente quando o dev fizer commit)
- `DEPLOY_LOG` — log de deploy

## 5. Atualizar checklist (Definition of Done)

```bash
# Listar checklist
curl -s http://127.0.0.1:9777/api/tasks/{CODE} | jq '.checklist'

# Marcar item como concluido
curl -X PATCH http://127.0.0.1:9777/api/tasks/checklist/{ITEM_ID}/toggle
```

## 6. Criar Code Review ANTES de mover para Revisao

**OBRIGATORIO**: Antes de mover qualquer tarefa para "Revisao", o agente
DEVE criar um comentario do tipo CODE_REVIEW com o resumo completo.

O code review deve conter:
- **Resumo** das alteracoes feitas
- **Arquivos modificados** (lista completa com paths)
- **Testes** realizados ou pendentes
- **Riscos/observacoes** relevantes
- **Checklist de qualidade**: lint, tipagem, testes, seguranca
- **Instrucoes para o dev**: como testar, o que verificar

```bash
# 6a. Criar o code review (OBRIGATORIO antes de mover)
curl -X POST http://127.0.0.1:9777/api/comments \\
  -H 'Content-Type: application/json' \\
  -d '{
    "taskId": TASK_ID,
    "body": "## Code Review\\n\\n### Resumo\\nDescricao do que foi feito...\\n\\n### Arquivos modificados\\n- `path/to/file1`\\n- `path/to/file2`\\n\\n### Testes\\n- [x] Testes unitarios passando\\n- [ ] Teste de integracao pendente\\n\\n### Riscos / Observacoes\\nNenhum risco identificado.\\n\\n### Checklist de qualidade\\n- [x] Sem erros de lint\\n- [x] Tipagem correta\\n- [x] Sem vulnerabilidades obvias\\n\\n### Para o desenvolvedor\\n- Testar X manualmente\\n- Verificar Y no browser\\n- Quando aprovado, fazer commit e push",
    "type": "CODE_REVIEW"
  }'

# 6b. Agora sim, mover para Revisao
curl -X POST http://127.0.0.1:9777/api/tasks/{CODE}/move \\
  -H 'Content-Type: application/json' \\
  -d '{"columnId": REVIEW_COLUMN_ID}'
```

**NAO mova para Revisao sem o CODE_REVIEW.** A API bloqueia essa acao.

## 7. Criar tarefa de revisao para o desenvolvedor (OBRIGATORIO)

**SEMPRE** crie uma tarefa de revisao para o desenvolvedor validar o trabalho.
Essa tarefa garante que nenhum codigo vai para producao sem revisao humana.

```bash
curl -X POST http://127.0.0.1:9777/api/tasks \\
  -H 'Content-Type: application/json' \\
  -d '{
    "projectId": PROJECT_ID,
    "title": "Revisar: TITULO_DA_TAREFA_ORIGINAL",
    "description": "## Tarefa original\\nCodigo: TASK_CODE\\n\\n## Resumo das alteracoes\\n- Descricao do que foi feito\\n\\n## Arquivos modificados\\n- path/to/file1\\n- path/to/file2\\n\\n## O que testar\\n- Verificar X\\n- Testar Y no browser\\n\\n## Pontos de atencao\\n- Nenhum risco identificado\\n\\n## Apos revisao\\n- Fazer commit e push se aprovado",
    "type": "CHORE",
    "priority": "HIGH",
    "requiresHuman": true
  }'
```

### Tarefa local x tarefa do board externo

- **Revisao para o dev** = card normal (`isLocal` ausente/false): precisa
  aparecer no board de todo mundo.
- **Lembrete pessoal** ("revisar o que o dev fez hoje") = `isLocal: true`:
  nao sobe para o board externo e nao entra no progresso/modulo. Ver
  `relay-api-agent` (secao "Tarefas locais").

### Regras da tarefa de revisao

- Tipo: **CHORE** com prioridade **HIGH**
- Flag `requiresHuman: true` — garante que outro agente nao pegue
- Titulo: "Revisar: [titulo da tarefa original]"
- Descricao deve conter: resumo, arquivos, o que testar, pontos de atencao
- Criar SEMPRE, mesmo para alteracoes pequenas

## 8. Informar o desenvolvedor

Apos mover para Revisao e criar a tarefa de revisao, o agente deve informar:

- Resumo do que foi implementado
- Lista de arquivos modificados
- Codigo da tarefa de revisao criada
- O que o dev precisa testar/validar
- Lembrar que commits e pushs sao responsabilidade do dev

**O agente NAO faz commit. O agente NAO faz push. O agente documenta, cria tarefa de revisao e informa.**
""",
    },
    {
        "id": "relay-project-setup",
        "name": "Project Setup",
        "category": "setup",
        "description": "Criar e configurar um novo projeto com labels, epicos, responsaveis e goals",
        "tags": ["setup", "project", "bootstrap"],
        "filename": "relay-project-setup",
        "content": """---
description: Create and configure a new project with labels and initial tasks
---

# Project Setup

Criar um projeto completo com estrutura inicial.

## 1. Criar projeto

```bash
curl -X POST http://127.0.0.1:9777/api/projects \\
  -H 'Content-Type: application/json' \\
  -d '{"name":"Nome do Projeto","key":"KEY","description":"Descricao do projeto"}'
```

Colunas criadas automaticamente: A fazer, Fazendo, Feito.

## 2. Criar labels (tags)

```bash
for label in '{"name":"frontend","color":"#4C6EF5"}' '{"name":"backend","color":"#2F9E44"}' '{"name":"infra","color":"#E8590C"}' '{"name":"docs","color":"#868E96"}'; do
  curl -X POST http://127.0.0.1:9777/api/labels \\
    -H 'Content-Type: application/json' -d "$label"
done
```

## 3. Criar epicos (agrupadores tematicos)

```bash
curl -X POST http://127.0.0.1:9777/api/projects/1/epics \\
  -H 'Content-Type: application/json' -d '{"name":"Cashier"}'
```

## 4. Cadastrar responsaveis

```bash
curl -X POST http://127.0.0.1:9777/api/projects/1/members \\
  -H 'Content-Type: application/json' -d '{"name":"Walter"}'
```

## 5. Criar tarefas iniciais (modelo simplificado)

```bash
curl -X POST http://127.0.0.1:9777/api/tasks \\
  -H 'Content-Type: application/json' \\
  -d '{"projectId":1,"title":"Setup do repositorio","priority":"HIGH","assignee":"Walter"}'
```

Vincular epico/tag depois de criar a tarefa:

```bash
curl -X POST http://127.0.0.1:9777/api/epics/1/tasks/1
curl -X POST http://127.0.0.1:9777/api/labels/1/tasks/1
```

## 6. Criar o primeiro goal

```bash
curl -X POST http://127.0.0.1:9777/api/projects/1/goals \\
  -H 'Content-Type: application/json' \\
  -d '{"name":"Entregar MVP","dueDate":"2026-12-31","tag":"mvp"}'
```

## 7. Adicionar dependencias entre cards

```bash
# KEY-2 so pode comecar depois de KEY-1
curl -X POST http://127.0.0.1:9777/api/tasks/KEY-2/dependencies \\
  -H 'Content-Type: application/json' -d '{"blockerCode":"KEY-1"}'
```
""",
    },
    {
        "id": "relay-sprint-planning",
        "name": "Sprint Planning",
        "category": "workflow",
        "description": "Planejar sprint: analisar metricas, priorizar backlog, estimar tarefas",
        "tags": ["sprint", "planning", "metrics"],
        "filename": "relay-sprint-planning",
        "content": """---
description: Sprint planning - analyze metrics, prioritize backlog, estimate tasks
---

# Sprint Planning

Auxiliar no planejamento de sprint usando dados do Relay.

```bash
# criar sprint com data de finalizacao (contagem regressiva nas metricas)
curl -X POST http://127.0.0.1:9777/api/projects/1/sprints \\
  -H 'Content-Type: application/json' -d '{"name":"Sprint 6","endDate":"2026-11-20"}'
# editar datas depois de criada
curl -X PATCH http://127.0.0.1:9777/api/sprints/2 \\
  -H 'Content-Type: application/json' -d '{"endDate":"2026-11-27"}'
```
- data de finalizacao da sprint (`endDate`) e previsao de entrega do projeto
  (`PATCH /api/projects/1 {"targetDate":"2026-12-31"}`) aparecem nas metricas
  como contagem regressiva ("X dias para fechar a sprint" /
  "X dias para finalizar o projeto")

## 1. Analisar metricas atuais

```bash
curl -s http://127.0.0.1:9777/api/projects/metrics | jq '.summary'
```

Metricas disponiveis:
- `totalTasks` / `doneTasks` — progresso geral
- `completedLast7d` / `completedLast30d` — velocidade recente
- `avgLeadTimeHours` — tempo medio criacao->conclusao

## 2. Listar backlog

```bash
# Tarefas no backlog, ordenadas por prioridade
curl -s 'http://127.0.0.1:9777/api/tasks?status=Backlog' | jq '.[] | {code, title, type, priority, estimateMd}'
```

## 3. Estimar tarefas

```bash
curl -X PATCH http://127.0.0.1:9777/api/tasks/{CODE} \\
  -H 'Content-Type: application/json' \\
  -d '{"estimateMd": 2.0}'
```

## 4. Priorizar e mover para "A fazer"

```bash
# Buscar coluna "A fazer"
curl -s http://127.0.0.1:9777/api/projects/{ID}/board | jq '.columns[] | select(.name=="A fazer") | .id'

# Mover tarefas selecionadas
curl -X POST http://127.0.0.1:9777/api/tasks/{CODE}/move \\
  -H 'Content-Type: application/json' -d '{"columnId": COLUMN_ID}'
```

## 5. Verificar capacidade

Velocidade media (tarefas/semana) vs soma de estimativas das tarefas selecionadas.
Use `avgCycleTimeHours` para estimar tempo medio por tarefa.

## 6. Documentar decisoes do sprint

```bash
curl -X POST http://127.0.0.1:9777/api/documents \\
  -H 'Content-Type: application/json' \\
  -d '{"projectId":1,"title":"Sprint Planning - Semana X","body":"## Objetivo\\n...","type":"NOTES"}'
```
""",
    },
    {
        "id": "relay-code-review-log",
        "name": "Code Review Log",
        "category": "workflow",
        "description": "Registrar resultados de code review em tarefas com comentarios tipados",
        "tags": ["review", "code", "quality"],
        "filename": "relay-code-review-log",
        "content": """---
description: Log code review results on tasks with typed comments
---

# Code Review Log

Registrar revisoes de codigo como comentarios tipados na tarefa.

## 1. Obter contexto da tarefa

```bash
curl -s http://127.0.0.1:9777/api/tasks/{CODE}/context | jq .
```

## 2. Adicionar review

```bash
curl -X POST http://127.0.0.1:9777/api/comments \\
  -H 'Content-Type: application/json' \\
  -d '{
    "taskId": TASK_ID,
    "body": "## Code Review\\n\\n**Aprovado com ressalvas**\\n\\n- Logica OK\\n- Falta teste para edge case X\\n- Sugestao: extrair metodo Y",
    "type": "CODE_REVIEW"
  }'
```

## 3. Registrar referencia ao commit

```bash
curl -X POST http://127.0.0.1:9777/api/comments \\
  -H 'Content-Type: application/json' \\
  -d '{
    "taskId": TASK_ID,
    "body": "commit abc1234 - fix: corrigir validacao de entrada",
    "type": "COMMIT_REF"
  }'
```

## 4. Atualizar checklist de DoD

```bash
# Marcar "Code review aprovado" no checklist
curl -X PATCH http://127.0.0.1:9777/api/tasks/checklist/{ITEM_ID}/toggle
```
""",
    },
    {
        "id": "relay-bug-triage",
        "name": "Bug Triage",
        "category": "workflow",
        "description": "Triagem de bugs: criar, classificar, priorizar e documentar",
        "tags": ["bug", "triage", "quality"],
        "filename": "relay-bug-triage",
        "content": """---
description: Bug triage - create, classify, prioritize and document bugs
---

# Bug Triage

Fluxo para triagem e registro de bugs.

## 1. Registrar bug

```bash
curl -X POST http://127.0.0.1:9777/api/tasks \\
  -H 'Content-Type: application/json' \\
  -d '{
    "projectId": PROJECT_ID,
    "title": "Descricao curta do bug",
    "type": "BUG",
    "priority": "HIGH",
    "description": "## Comportamento atual\\n...\\n\\n## Comportamento esperado\\n...\\n\\n## Passos para reproduzir\\n1. ...\\n2. ...\\n3. ..."
  }'
```

## 2. Adicionar checklist de investigacao

```bash
for item in 'Reproduzir o bug' 'Identificar causa raiz' 'Implementar fix' 'Adicionar teste de regressao' 'Validar em staging'; do
  curl -X POST http://127.0.0.1:9777/api/tasks/{CODE}/checklist \\
    -H 'Content-Type: application/json' -d "{\\\"title\\\":\\\"$item\\\"}"
done
```

## 3. Classificar com labels

```bash
# Aplicar label de area afetada
curl -X POST http://127.0.0.1:9777/api/labels/{LABEL_ID}/tasks/{TASK_ID}
```

## 4. Documentar investigacao

```bash
curl -X POST http://127.0.0.1:9777/api/comments \\
  -H 'Content-Type: application/json' \\
  -d '{"taskId":TASK_ID,"body":"Causa raiz: query sem indice na tabela X","type":"COMMENT"}'
```
""",
    },
    {
        "id": "relay-daily-standup",
        "name": "Daily Standup",
        "category": "workflow",
        "description": "Gerar resumo para daily standup: o que foi feito, o que esta em andamento, bloqueios",
        "tags": ["daily", "standup", "report"],
        "filename": "relay-daily-standup",
        "content": """---
description: Generate daily standup summary - done, in progress, blockers
---

# Daily Standup

Gerar resumo automatico para daily standup.

## 1. Tarefas concluidas recentemente

```bash
curl -s 'http://127.0.0.1:9777/api/tasks?status=Conclu%C3%ADdo' | \\
  jq '[.[] | select(.updatedAt > "ONTEM") | {code, title, type}]'
```

## 2. Tarefas em andamento

```bash
curl -s 'http://127.0.0.1:9777/api/tasks?status=Fazendo' | \\
  jq '.[] | {code, title, type, priority}'
```

## 3. Tarefas bloqueadas

```bash
# Buscar tarefas que tem dependencias nao resolvidas
curl -s 'http://127.0.0.1:9777/api/tasks?status=Fazendo' | \\
  jq '.[] | select(.blockedBy | length > 0) | {code, title, blockedBy: [.blockedBy[].code]}'
```

## 4. Atividade recente

```bash
curl -s 'http://127.0.0.1:9777/api/activity?limit=20' | \\
  jq '.[] | {action, detail, createdAt}'
```

## 5. Quem chegou em cada estagio (fluxo, nao foto)

```bash
curl -s "http://127.0.0.1:9777/api/projects/1/metrics/stages?stage=dev-box" | jq '{
  total,
  estagios: [.stages[] | {name, reached, pct, current}],
  dev_box_por_modulo: .selected.groups
}'
```

`reached` = neste estagio ou depois (posicao atual); `current` = esta ali agora;
`current` = esta ali agora. O corte por modulo soma 100%.

## 6. Metricas do dia

```bash
curl -s http://127.0.0.1:9777/api/projects/metrics | \\
  jq '{completedLast7d: .summary.completedLast7d, avgLeadTimeHours: .summary.avgLeadTimeHours}'
```
""",
    },
    {
        "id": "relay-tech-debt-tracker",
        "name": "Tech Debt Tracker",
        "category": "management",
        "description": "Rastrear e gerenciar divida tecnica com tarefas tipadas e metricas",
        "tags": ["tech-debt", "management", "quality"],
        "filename": "relay-tech-debt-tracker",
        "content": """---
description: Track and manage technical debt with typed tasks and metrics
---

# Tech Debt Tracker

Gerenciar divida tecnica de forma sistematica.

## 1. Registrar divida tecnica

```bash
curl -X POST http://127.0.0.1:9777/api/tasks \\
  -H 'Content-Type: application/json' \\
  -d '{
    "projectId": PROJECT_ID,
    "title": "Refatorar modulo de autenticacao",
    "type": "TECH_DEBT",
    "priority": "MEDIUM",
    "description": "## Problema\\nCodigo duplicado em 3 controllers...\\n\\n## Impacto\\nDificulta manutencao...\\n\\n## Proposta\\nExtrair para middleware compartilhado",
    "estimateMd": 3.0
  }'
```

## 2. Ver panorama de divida tecnica

```bash
curl -s 'http://127.0.0.1:9777/api/tasks?status=Backlog' | \\
  jq '[.[] | select(.type == "TECH_DEBT") | {code, title, priority, estimateMd}]'
```

## 3. Calcular esforco total

```bash
curl -s 'http://127.0.0.1:9777/api/tasks' | \\
  jq '[.[] | select(.type == "TECH_DEBT" and .status != "Concluido") | .estimateMd // 0] | add'
```

## 4. Metricas de divida vs features

```bash
curl -s http://127.0.0.1:9777/api/projects/metrics | \\
  jq '.byType | {tech_debt: .TECH_DEBT, features: .FEATURE}'
```
""",
    },
    {
        "id": "relay-documentation-writer",
        "name": "Documentation Writer",
        "category": "management",
        "description": "Criar e gerenciar documentos tecnicos vinculados a projetos e tarefas",
        "tags": ["docs", "documentation", "writing"],
        "filename": "relay-documentation-writer",
        "content": """---
description: Create and manage technical documents linked to projects and tasks
---

# Documentation Writer

Gerenciar documentos tecnicos no Relay Local.

## 1. Criar documento de projeto

```bash
curl -X POST http://127.0.0.1:9777/api/documents \\
  -H 'Content-Type: application/json' \\
  -d '{
    "projectId": PROJECT_ID,
    "title": "Arquitetura do Sistema",
    "body": "# Arquitetura\\n\\n## Componentes\\n...",
    "type": "NOTES"
  }'
```

## 2. Criar documento vinculado a tarefa

```bash
curl -X POST http://127.0.0.1:9777/api/documents \\
  -H 'Content-Type: application/json' \\
  -d '{
    "taskId": TASK_ID,
    "title": "Especificacao Tecnica - Feature X",
    "body": "# Spec\\n\\n## Requisitos\\n...",
    "type": "NOTES"
  }'
```

## 3. Listar documentos

```bash
# Por projeto
curl -s 'http://127.0.0.1:9777/api/documents?projectId=1' | jq '.[] | {id, title, type, version}'

# Por tarefa
curl -s 'http://127.0.0.1:9777/api/documents?taskId=1' | jq '.[] | {id, title, type, version}'
```

## 4. Atualizar documento (versionado)

```bash
curl -X PUT http://127.0.0.1:9777/api/documents/{DOC_ID} \\
  -H 'Content-Type: application/json' \\
  -d '{"title":"Titulo atualizado","body":"# Conteudo revisado\\n..."}'
```

Cada PUT incrementa a versao automaticamente.
""",
    },
    {
        "id": "relay-daily-report",
        "name": "Daily Report",
        "category": "workflow",
        "description": "Gerar relatorio diario: criar nota, registrar atividades e gerar resumo via API",
        "tags": ["daily", "report", "notes", "tracking"],
        "filename": "relay-daily-report",
        "content": """---
description: Generate daily report - create notes, track activity, generate summary via API
---

# Daily Report

Fluxo para o agente criar e gerar o relatorio diario do usuario.
Suporta dois modos: **parcial** (status do dia ate agora) e **completo** (fechamento do dia).

## Detectar modo de uso

O agente deve identificar qual modo usar com base no pedido do usuario:

| Pedido do usuario | Modo |
|---|---|
| "como esta meu dia", "status do dia", "o que fiz hoje", "resumo parcial" | **Parcial** |
| "gerar relatorio do dia", "fechar o dia", "relatorio final", "resumo do dia" | **Completo** |

Se o pedido for ambiguo, pergunte: "Quer um status parcial de como esta o dia ate agora, ou o relatorio completo de fechamento?"

---

## MODO PARCIAL — Status do dia ate agora

Use quando o usuario quer apenas verificar como esta o dia, sem fechar.
NAO gera relatorio formal nem resumo final. Apenas apresenta o estado atual.

### Passo 1 — Coletar dados

```bash
# Data de hoje
DATE=$(date +%F)

# Nota do dia (foco planejado, bloqueios, anotacoes)
curl -s http://127.0.0.1:9777/api/daily/$DATE | jq '{notes: .notes, report: .report}'

# Atividade no board hoje
curl -s http://127.0.0.1:9777/api/daily/$DATE/activity | jq .

# Atividade recente geral
curl -s http://127.0.0.1:9777/api/activity?limit=15 | jq '.[] | {action, detail, createdAt}'

# Tarefas em andamento (coluna "Fazendo")
curl -s http://127.0.0.1:9777/api/tasks?status=Fazendo | jq '.[] | {code, title, type, priority}'
```

### Passo 2 — Apresentar status

Apresente ao usuario de forma conversacional:

```
Status do dia — YYYY-MM-DD

Foco planejado: (extrair da nota do dia, se existir)
- ...

Em andamento agora:
- PROJ-1: Titulo da tarefa (tipo, prioridade)
- ...

Feito ate agora:
- Descricao curta da atividade
- ...

Bloqueios: (extrair da nota ou inferir de tarefas bloqueadas)
- ...
```

### Regras do modo parcial

- NAO chamar `POST /api/daily/{date}/report` (nao gerar relatorio formal)
- NAO salvar resumo na nota do dia
- NAO adicionar secao de analise
- Apresentar de forma leve e conversacional
- Se nao houver nota do dia, informar e sugerir criar uma
- Se nao houver atividade, informar que o dia esta vazio ate agora

---

## MODO COMPLETO — Relatorio de fechamento do dia

Use quando o usuario quer gerar o relatorio final.

### IMPORTANTE: A nota do dia e o conteudo PRINCIPAL do relatorio

O relatorio e gerado a partir da nota do dia (body da DailyNote). O conteudo
da nota aparece INTEIRO no topo do relatorio, preservando todas as secoes.

As atividades do board e timeline sao COMPLEMENTARES — aparecem abaixo da
nota do dia como "Tarefas do Board" e "Timeline de Atividades".

### Template de nota diaria

O template padrao e simples — apenas checklist:

```markdown
## Foco do Dia
- [ ] ...

## Bloqueios
- ...

## Notas
- ...
```

### 1. Verificar nota existente do dia

```bash
curl -s http://127.0.0.1:9777/api/daily/$(date +%F)
```

Se a nota ja existe, leia o body para entender o contexto do dia.

### 2. Criar nota do dia (se nao existe)

```bash
curl -X PUT http://127.0.0.1:9777/api/daily/$(date +%F) \\
  -H 'Content-Type: application/json' \\
  -d '{"body":"## Foco do Dia\\n- [ ] Implementar modulo X\\n..."}'
```

### 3. Atualizar nota do dia

```bash
curl -X PATCH http://127.0.0.1:9777/api/daily/$(date +%F) \\
  -H 'Content-Type: application/json' \\
  -d '{"body":"## Foco do Dia\\n- [x] Implementar modulo X\\n- [ ] Modulo Y\\n..."}'
```

Use PATCH para atualizar secoes especificas sem perder o que ja existe.

### 4. Ver atividade do dia (complementar)

```bash
curl -s http://127.0.0.1:9777/api/daily/$(date +%F)/activity
```

Retorna tarefas que tiveram atividade no board.
Use para ENRIQUECER a nota — adicione itens nos checkpoints.

### 5. Gerar relatorio base do dia

```bash
curl -X POST http://127.0.0.1:9777/api/daily/$(date +%F)/report
```

O relatorio inclui:
1. Conteudo completo da nota do dia (topo)
2. Tarefas do board que tiveram atividade
3. Timeline de atividades
4. Resumo automatico

### 6. Adicionar analise ao relatorio

```bash
curl -X PATCH http://127.0.0.1:9777/api/daily/$(date +%F)/report \\
  -H 'Content-Type: application/json' \\
  -d '{"content":"## Analise\\n- ..."}'
```

### Fluxo recomendado (completo)

1. Verificar se ja existe nota (`GET /api/daily/{date}`)
2. Se existe: ler o body
3. Se nao existe: criar com template (`PUT /api/daily/{date}`)
4. Verificar atividade do board (`GET /api/daily/{date}/activity`)
5. Atualizar nota com informacoes novas (`PATCH /api/daily/{date}`)
6. Gerar relatorio (`POST /api/daily/{date}/report`)
7. **Gerar resumo final** (ver secao abaixo)

### 7. Resumo final para registro de trabalho

Ao final do fluxo, SEMPRE gere um resumo simples para registro de trabalho.
O resumo deve ser uma bullet list direta, sem codigo, sem detalhes tecnicos,
sem explicacoes longas — apenas o que foi feito no dia.

#### Formato obrigatorio

```markdown
## Resumo do dia — YYYY-MM-DD

- Tarefa/atividade descrita de forma simples e curta
- Outra tarefa ou atividade
- ...
```

#### Exemplo

```markdown
## Resumo do dia — 2026-06-26

- Implementacao do modulo de notificacoes
- Correcao de bug no login com Google
- Revisao de PR do fluxo de pagamento
- Reuniao de alinhamento com o time de produto
- Atualizacao da documentacao da API
```

#### Regras do resumo

- Uma linha por item, comecando com `-`
- Linguagem simples e direta (sem jargao tecnico desnecessario)
- NAO incluir: trechos de codigo, nomes de arquivos, hashes de commit, stack traces
- NAO incluir: detalhes de implementacao ("adicionei campo X na tabela Y")
- SIM incluir: o QUE foi feito em alto nivel ("implementacao do modulo de relatorios")
- Manter entre 3 e 15 itens — agrupar atividades menores relacionadas
- Usar verbos no passado ou infinitivo ("Implementacao de...", "Correcao de...")

O resumo deve ser exibido ao usuario no final da conversa E salvo na nota do dia
via `PATCH /api/daily/{date}` — adicionado ao final do body existente.

---

## Dicas gerais

- A nota do dia e a FONTE PRINCIPAL do relatorio
- O relatorio preserva o conteudo da nota inteiro no topo
- Use `GET /api/daily/{date}/activity` para complementar
- A data sempre no formato ISO: YYYY-MM-DD
- No modo completo, o resumo final e obrigatorio — nao encerre sem gera-lo
- No modo parcial, NAO salve nada — apenas apresente o status
- Use `$(date +%F)` para obter a data atual automaticamente
""",
    },
    {
        "id": "relay-context-loader",
        "name": "Context Loader",
        "category": "agent",
        "description": "Carregar contexto completo dos projetos, boards e tarefas para continuar de onde parou",
        "tags": ["context", "board", "project", "resume", "continuidade"],
        "filename": "relay-context-loader",
        "content": """---
description: Load full workspace context - projects, boards, tasks, activity - to resume work from where you left off
---

# Context Loader — Retomar Contexto do Workspace

Use esta skill no inicio de cada sessao para entender o estado atual do
workspace e continuar o trabalho de onde parou.

## OBJETIVO

Antes de executar qualquer tarefa, o agente DEVE conhecer:
- Quais projetos existem e seus boards
- Quais tarefas estao em andamento, bloqueadas ou pendentes
- O que foi feito recentemente (atividade)
- Notas e relatorio do dia

Com esse contexto, o agente pode tomar decisoes informadas e
continuar de pontos anteriores sem perder historico.

## PASSO 1 — Verificar conexao

```bash
curl -s http://127.0.0.1:9777/api/health | jq .
```

## PASSO 2 — Listar todos os projetos

```bash
curl -s http://127.0.0.1:9777/api/projects | jq '.[] | {id, name, key, description}'
```

Armazene os IDs e keys dos projetos para os proximos passos.

## PASSO 3 — Carregar board de cada projeto

Para cada projeto retornado no passo 2:

```bash
curl -s http://127.0.0.1:9777/api/projects/{PROJECT_ID}/board | jq '{
  project: .project.name,
  columns: [.columns[] | {
    name: .name,
    position: .position,
    wipLimit: .wipLimit,
    tasks: [.tasks[] | {
      code: .code,
      title: .title,
      type: .type,
      priority: .priority,
      assignee: .assignee,
      dueDate: .dueDate,
      blocked: .blocked,
      requiresHuman: .requiresHuman,
      labels: [.labels[]?.name]
    }]
  }]
}'
```

### O que observar no board

- **Tarefas em "Fazendo"**: trabalho em andamento — verifique se deve continuar
- **Tarefas bloqueadas** (`blocked: true`): identificar o motivo e se pode desbloquear
- **Tarefas vencidas** (`dueDate` no passado): prioridade alta
- **Tarefas com `requiresHuman: true`**: NAO tocar, sao exclusivas do dev
- **WIP limits**: respeitar o limite de tarefas por coluna

## PASSO 4 — Metricas dos projetos

```bash
curl -s http://127.0.0.1:9777/api/projects/metrics | jq '.[] | {
  project: .name,
  total: .total,
  done: .done,
  inProgress: .inProgress,
  overdue: .overdue
}'
```

## PASSO 5 — Atividade recente

```bash
curl -s http://127.0.0.1:9777/api/activity?limit=20 | jq '.[] | {
  action: .action,
  entity: .entityType,
  detail: .detail,
  timestamp: .createdAt
}'
```

A atividade mostra o que foi feito recentemente: tarefas criadas,
movidas, comentadas, concluidas. Use para entender o ritmo e o
contexto do trabalho em andamento.

## PASSO 6 — Notas e relatorio do dia

```bash
# Nota de hoje
curl -s http://127.0.0.1:9777/api/daily/$(date +%F) | jq '{notes: .notes, report: .report}'

# Atividade do dia
curl -s http://127.0.0.1:9777/api/daily/$(date +%F)/activity | jq .
```

As notas do dia contem o foco planejado, bloqueios e decisoes.
O relatorio contem o resumo do que foi feito.

## PASSO 7 — Contexto de tarefas especificas

Para qualquer tarefa que precise de mais detalhes:

```bash
# Contexto completo (tarefa + comentarios + docs + atividade)
curl -s http://127.0.0.1:9777/api/tasks/{CODE}/context | jq .

# Fluxo da tarefa (grafo de dependencias)
curl -s http://127.0.0.1:9777/api/tasks/{CODE}/flow | jq .
```

## PASSO 8 — Historico de desenvolvimento por tarefa

O endpoint `/history` retorna a timeline estruturada de uma tarefa:
transicoes de coluna, comentarios, code reviews, progresso do checklist.
Use para entender o historico completo de uma tarefa antes de continuar.

```bash
curl -s http://127.0.0.1:9777/api/tasks/{CODE}/history | jq '{
  task: .task.code,
  status: .currentStatus,
  columnFlow: .columnFlow,
  checklist: .checklist,
  hasCodeReview: .hasCodeReview,
  commentCount: .commentCount,
  timeline: [.timeline[] | {type, action, detail, timestamp}]
}'
```

### O que observar no historico

- **columnFlow**: sequencia de transicoes (ex: "Backlog -> A Fazer -> Fazendo")
- **hasCodeReview**: se ja tem code review registrado
- **checklist**: progresso do Definition of Done
- **timeline**: todos os eventos em ordem cronologica

## PASSO 9 — Changelog do projeto

O endpoint `/changelog` retorna o historico agregado de um projeto
nos ultimos N dias (padrao: 7). Use para entender o ritmo do projeto.

```bash
curl -s "http://127.0.0.1:9777/api/projects/{PROJECT_ID}/changelog?days=7" | jq '{
  project: .project.name,
  summary: .summary,
  completed: [.completed[] | {code, title, type}],
  inProgress: [.inProgress[] | {code, title, assignee}],
  recentComments: [.recentComments[:5][] | {taskCode, type, body}]
}'
```

### O que observar no changelog

- **summary.completedInPeriod**: velocidade de entrega
- **summary.inProgress**: trabalho ativo
- **completed**: o que foi entregue — contexto para continuar
- **inProgress**: tarefas em andamento — verificar se precisa ajuda
- **activityByDay**: ritmo diario de atividade

## PASSO 10 — Labels disponiveis

```bash
curl -s http://127.0.0.1:9777/api/labels | jq '.[] | {id, name, color}'
```

## PASSO 11 — Memoria agentic do workspace

A memoria agentic guarda fatos, decisoes, preferencias, episodios e
procedimentos com busca hibrida (semantica + keywords). Use SEMPRE ao
iniciar a sessao para recuperar contexto de qualquer ponto do projeto.

```bash
# Estatisticas
curl -s http://127.0.0.1:9777/api/memory/stats | jq .

# Busca semantica (troque a query pelo foco da sessao)
curl -s -X POST http://127.0.0.1:9777/api/memory/search   -H 'Content-Type: application/json'   -d '{"query":"decisoes de arquitetura e preferencias do projeto","topK":8}'   | jq '{count, agentContext, results: [.results[] | {id, kind, title, score}]}'

# Listar decisoes recentes
curl -s 'http://127.0.0.1:9777/api/memory?kind=decision&limit=20' | jq .

# Gravar memoria nova (quando aprender algo importante)
curl -s -X POST http://127.0.0.1:9777/api/memory   -H 'Content-Type: application/json'   -d '{"title":"...","content":"...","kind":"decision","importance":0.8,"sourceType":"agent"}' | jq .

# Ingerir entidade existente (task|comment|document|daily|recording|sprint|kb)
curl -s -X POST http://127.0.0.1:9777/api/memory/ingest   -H 'Content-Type: application/json'   -d '{"sourceType":"task","sourceId":123}' | jq .
```

### Kinds disponiveis
- `fact` — fato objetivo
- `decision` — decisao de arquitetura/produto
- `preference` — preferencia do dev/time
- `episode` — o que aconteceu (reuniao, incidente)
- `procedure` — como fazer algo
- `context` — contexto geral de tarefa/projeto

## RESUMO DO CONTEXTO

Apos executar os passos acima, o agente deve montar mentalmente:

1. **Mapa do workspace**: projetos → colunas → tarefas
2. **Trabalho em andamento**: tarefas em "Fazendo" e quem esta nelas
3. **Proximas tarefas**: o que esta em "A Fazer" ou "Backlog" com maior prioridade
4. **Bloqueios**: tarefas bloqueadas e seus motivos
5. **Historico recente**: ultimas acoes para entender o fluxo
6. **Foco do dia**: notas e planejamento do dev
7. **Historico de tarefas ativas**: timeline de cada tarefa em andamento
8. **Changelog do projeto**: o que foi feito nos ultimos dias
9. **Memoria agentic**: decisoes, preferencias e episodios relevantes

Com esse mapa, o agente pode:
- Continuar uma tarefa em andamento de onde parou
- Pegar a proxima tarefa mais prioritaria
- Desbloquear tarefas pendentes
- Reportar o estado atual ao dev
- Revisar o que foi feito antes de avancar
- Reusar decisoes e preferencias ja registradas na memoria

## DICA

Execute esta skill sempre que iniciar uma nova conversa ou
quando mudar de workspace. O contexto muda frequentemente
e o agente deve estar sempre atualizado.

Para revisao de contexto rapida, use os passos 8, 9 e 11
(historico da tarefa + changelog + busca na memoria).
""",
    },
    {
        "id": "relay-use",
        "name": "Relay Use (orquestrador)",
        "category": "agent",
        "description": "Mini skill: analisa o momento atual e escolhe quais skills Relay usar agora",
        "tags": ["router", "orchestrator", "skills", "workflow", "momento", "use"],
        "filename": "relay-use",
        "content": """---
description: Analyze the current moment and pick the right Relay skills to run now. Trigger with /relay-use or when unsure what to do next in Relay.
---

# relay-use — Orquestrador de skills

Mini skill de **roteamento**. Nao substitui as outras skills: decide **quais**
usar agora com base na conversa + estado do workspace, e executa o primeiro passo.

Base API: `http://127.0.0.1:9777/api`

## QUANDO USAR

- Inicio de sessao ou "o que faco agora no Relay?"
- Depois de varias acoes no chat e precisar reorganizar o fluxo
- Quando o agente estiver perdido entre board / memoria / diario / review
- Comando OpenCode: `/relay-use [foco opcional]`

## PASSO 0 — Snapshot (paralelo, obrigatorio)

```bash
curl -s http://127.0.0.1:9777/api/health | jq .
curl -s http://127.0.0.1:9777/api/projects | jq '.[] | {id,key,name}'
curl -s 'http://127.0.0.1:9777/api/activity?limit=15' | jq '.[:10]'
curl -s http://127.0.0.1:9777/api/daily/$(date +%F) | jq '{notes, report}'
curl -s -X POST http://127.0.0.1:9777/api/memory/search \\
  -H 'Content-Type: application/json' \\
  -d '{"query":"contexto da sessao decisoes preferencias","topK":5}' \\
  | jq '{count, agentContext}'
```

API offline → so `relay-run`. Pare.

## PASSO 1 — Classificar o momento (1 primario + ate 2 secundarios)

| Momento | Sinais |
|---------|--------|
| `boot` | sessao nova, continuar, onde paramos |
| `planejar` | sprint, priorizar, backlog |
| `executar` | feature/bug em andamento, codando |
| `revisar` | review, PR, coluna Revisao |
| `documentar` | ADR, spec, documentar decisao |
| `memorizar` | "lembra", preferencia, licao |
| `diario` | standup, fim do dia, relatorio |
| `setup` | projeto novo, labels, primeiro uso |
| `lideranca` | goals, metricas por pessoa, acompanhamento |
| `incidente` | bug urgente, hotfix, prod |
| `estudo` | aprender, plano de estudo |

Leia tambem o historico **desta conversa**.

## PASSO 2 — Mapa skill → momento

| Skill | Momentos |
|-------|----------|
| `relay-run` | API down |
| `relay-context-loader` | boot |
| `relay-agentic-memory` | boot, memorizar, documentar, executar |
| `relay-api-agent` | qualquer fluxo REST |
| `relay-task-workflow` | executar |
| `relay-project-setup` | setup |
| `relay-goals` | lideranca, planejar |
| `relay-members` | lideranca, executar |
| `relay-sprint-planning` | planejar |
| `relay-code-review-log` | revisar |
| `relay-bug-triage` | incidente |
| `relay-daily-standup` | diario (manha) |
| `relay-daily-report` | diario (fim do dia) |
| `relay-tech-debt-tracker` | divida tecnica |
| `relay-documentation-writer` | documentar |
| `relay-use` | reavaliar o roteamento |

## PASSO 3 — Formato da resposta

```markdown
## Momento
- Primario: …
- Secundarios: …
- Evidencias: …

## Skills agora
1. **id** — por que
2. …

## Proximas acoes
1. …
2. …

## Ja faco agora
(executar a 1a acao util)
```

Maximo **3 skills**. Prefira acao a catalogo.

## PASSO 4 — Executar o primeiro passo

| Momento | Acao imediata |
|---------|----------------|
| boot | context-loader essencial + memory search |
| executar (sem task) | criar task + mover para Fazendo |
| decisao na conversa | POST /api/memory (kind=decision) |
| fim de task | comentario + move Revisao |
| fim do dia | daily-report |
| incidente | bug-triage + task URGENT |

## Atalhos de frase

- "continuar" → context-loader + memory + board Fazendo
- "o que fazer" → board + metrics + preferences na memory
- "review" → code-review-log
- "anota/lembra" → agentic-memory remember
- "fechei o dia" → daily-report
- "bug em prod" → bug-triage
- "projeto novo" → project-setup
- "goal" ou "progresso" → relay-goals
- "quem faz" ou "responsavel" → relay-members

## Regras

- Nao inventar projectId/codes — ler da API
- Respeitar `requiresHuman`
- Se incerto, caminho de menor risco + alternativa em 1 linha
- OpenCode: tools `relay_*` + comando `/relay-use`
""",
    },
    {
        "id": "relay-agentic-memory",
        "name": "Agentic Memory",
        "category": "agent",
        "description": "Usar a memória agentic do workspace: buscar, gravar, ingerir e consultar decisões/contexto",
        "tags": ["memory", "agent", "context", "semantic", "knowledge", "decisions"],
        "filename": "relay-agentic-memory",
        "content": """---
description: Use workspace agentic memory - hybrid semantic search, remember facts/decisions, ingest entities
---

# Agentic Memory — Memoria do Workspace para Agentes

Base URL: `http://127.0.0.1:9777/api`

A memoria agentic e **por workspace** (SQLite isolado). Guarda fatos, decisoes,
preferencias, episodios e procedimentos com busca hibrida (embedding + keywords).
Use para que o agente tenha contexto de qualquer ponto do desenvolvimento.

## QUANDO USAR

- **Inicio de sessao**: buscar memoria relevante ao foco do dia
- **Apos decisao importante**: gravar com `kind=decision`
- **Preferencia do dev/time**: gravar com `kind=preference`
- **Apos reuniao/code review/ADR**: ingerir a entidade fonte
- **Antes de implementar**: consultar decisoes e procedimentos existentes
- **Liçao aprendida / incidente**: gravar com `kind=episode`

## KINDS

| kind | Uso |
|------|-----|
| `fact` | Fato objetivo e estavel |
| `decision` | Decisao de arquitetura, produto ou processo |
| `preference` | Preferencia do dev/time (estilo, stack, convençao) |
| `episode` | O que aconteceu (reuniao, incidente, entrega) |
| `procedure` | Como fazer algo (runbook curto, passo a passo) |
| `context` | Contexto geral de tarefa/projeto |

## PASSO 1 — Verificar conexao e estatisticas

```bash
curl -s http://127.0.0.1:9777/api/health | jq .
curl -s http://127.0.0.1:9777/api/memory/stats | jq .
curl -s http://127.0.0.1:9777/api/memory/kinds | jq .
```

## PASSO 2 — Buscar memoria (sempre no inicio)

A busca retorna `results` + `agentContext` (markdown pronto para o agente).

```bash
curl -s -X POST http://127.0.0.1:9777/api/memory/search \\
  -H 'Content-Type: application/json' \\
  -d '{
    "query": "decisoes de arquitetura e preferencias do projeto",
    "topK": 8
  }' | jq '{count, agentContext, results: [.results[] | {id, kind, title, score, summary}]}'
```

### Filtros opcionais

```bash
# So decisoes de um projeto
curl -s -X POST http://127.0.0.1:9777/api/memory/search \\
  -H 'Content-Type: application/json' \\
  -d '{"query":"autenticacao jwt","kind":"decision","projectId":1,"topK":5}' | jq .

# Varios kinds
curl -s -X POST http://127.0.0.1:9777/api/memory/search \\
  -H 'Content-Type: application/json' \\
  -d '{"query":"deploy","kind":"procedure,decision","topK":6}' | jq .
```

## PASSO 3 — Listar memórias

```bash
# Recentes
curl -s 'http://127.0.0.1:9777/api/memory?limit=20' | jq '.[] | {id, kind, title, importance, tags}'

# Por kind
curl -s 'http://127.0.0.1:9777/api/memory?kind=decision&limit=20' | jq .

# Por projeto + texto
curl -s 'http://127.0.0.1:9777/api/memory?projectId=1&q=auth&limit=20' | jq .

# Por tarefa
curl -s 'http://127.0.0.1:9777/api/memory?taskId=42' | jq .
```

## PASSO 4 — Gravar memoria (remember)

```bash
curl -s -X POST http://127.0.0.1:9777/api/memory \\
  -H 'Content-Type: application/json' \\
  -d '{
    "title": "Auth via JWT Bearer",
    "content": "API usa JWT no header Authorization. Refresh token em cookie httpOnly. Nao usar sessions server-side.",
    "kind": "decision",
    "summary": "JWT Bearer + refresh em cookie",
    "tags": ["auth", "api", "seguranca"],
    "projectId": 1,
    "importance": 0.85,
    "sourceType": "agent"
  }' | jq '{id, kind, title, hasEmbedding}'
```

### Exemplos por kind

```bash
# Preferencia
curl -s -X POST http://127.0.0.1:9777/api/memory \\
  -H 'Content-Type: application/json' \\
  -d '{"title":"Commits em portugues","content":"Mensagens de commit e branches em portugues.","kind":"preference","importance":0.7,"sourceType":"agent"}' | jq .

# Procedimento
curl -s -X POST http://127.0.0.1:9777/api/memory \\
  -H 'Content-Type: application/json' \\
  -d '{"title":"Rodar testes locais","content":"cd local-client && source .venv/bin/activate && pytest -q","kind":"procedure","tags":["test","dev"],"sourceType":"agent"}' | jq .

# Episodio
curl -s -X POST http://127.0.0.1:9777/api/memory \\
  -H 'Content-Type: application/json' \\
  -d '{"title":"Incidente deploy 2026-07-20","content":"Falha por migration faltando. Corrigido com alembic upgrade head antes do start.","kind":"episode","importance":0.75,"sourceType":"agent"}' | jq .
```

### Regras ao gravar

- Titulo curto e buscavel; content completo e autocontido
- `importance` 0.0–1.0 (decisoes criticas >= 0.8)
- Sempre `sourceType: "agent"` quando o agente grava
- Vincule `projectId` / `taskId` quando souber
- Nao grave segredos (tokens, senhas, chaves)

## PASSO 5 — Ingerir entidades existentes

Converte task, comentario, documento, diario, reuniao, sprint ou nota KB
em entradas de memoria estruturadas.

```bash
# Tarefa
curl -s -X POST http://127.0.0.1:9777/api/memory/ingest \\
  -H 'Content-Type: application/json' \\
  -d '{"sourceType":"task","sourceId":123}' | jq .

# Code review / comentario
curl -s -X POST http://127.0.0.1:9777/api/memory/ingest \\
  -H 'Content-Type: application/json' \\
  -d '{"sourceType":"comment","sourceId":45}' | jq .

# ADR / SPEC / PLAN
curl -s -X POST http://127.0.0.1:9777/api/memory/ingest \\
  -H 'Content-Type: application/json' \\
  -d '{"sourceType":"document","sourceId":10}' | jq .

# Diario do dia
curl -s -X POST http://127.0.0.1:9777/api/memory/ingest \\
  -H 'Content-Type: application/json' \\
  -d '{"sourceType":"daily","sourceId":3}' | jq .

# Reuniao
curl -s -X POST http://127.0.0.1:9777/api/memory/ingest \\
  -H 'Content-Type: application/json' \\
  -d '{"sourceType":"recording","sourceId":7}' | jq .

# Sprint (meta + retro)
curl -s -X POST http://127.0.0.1:9777/api/memory/ingest \\
  -H 'Content-Type: application/json' \\
  -d '{"sourceType":"sprint","sourceId":2}' | jq .

# Nota KB
curl -s -X POST http://127.0.0.1:9777/api/memory/ingest \\
  -H 'Content-Type: application/json' \\
  -d '{"sourceType":"kb","sourceId":5}' | jq .
```

`sourceType` validos: `task` | `comment` | `document` | `daily` | `recording` | `sprint` | `kb`

## PASSO 6 — Perguntar a memoria (Q&A)

```bash
curl -s -X POST http://127.0.0.1:9777/api/memory/ask \\
  -H 'Content-Type: application/json' \\
  -d '{"question":"Como autenticamos a API?","projectId":1,"topK":6}' \\
  | jq '{answer, sources}'
```

## PASSO 7 — Atualizar / remover

```bash
# Atualizar
curl -s -X PATCH http://127.0.0.1:9777/api/memory/12 \\
  -H 'Content-Type: application/json' \\
  -d '{"content":"Texto atualizado da decisao","importance":0.9}' | jq .

# Soft-delete
curl -s -X DELETE http://127.0.0.1:9777/api/memory/12 | jq .
```

## PASSO 8 — Reembed (se o provedor de embeddings mudou)

```bash
curl -s -X POST http://127.0.0.1:9777/api/memory/reembed \\
  -H 'Content-Type: application/json' \\
  -d '{"onlyMissing":true,"limit":200}' | jq .
```

## FLUXO RECOMENDADO DO AGENTE

1. `POST /memory/search` com o foco da sessao → ler `agentContext`
2. Trabalhar com board/tarefas normalmente
3. Ao aprender algo estavel → `POST /memory` (remember)
4. Ao fechar tarefa importante / ADR / review → `POST /memory/ingest`
5. Antes de decidir arquitetura → search kind=decision + ask

## OpenCode tools (se disponiveis)

- `relay_searchMemory` — busca hibrida
- `relay_remember` — gravar
- `relay_listMemory` — listar
- `relay_ingestMemory` — ingerir fonte

## DICAS

- Memoria != KB: KB e notas humanas com backlinks `[[titulo]]`; memoria e
  estruturada para agentes (kinds, scores, ingest, agentContext)
- Sem embedding no provedor, a busca cai em keywords — ainda funciona
- Escopo = workspace ativo; ao trocar workspace a memoria muda
- Prefira poucas memórias densas a muitas fragmentadas
- Nunca armazene segredos
""",
    },
    {
        "id": "relay-project-daily",
        "name": "Daily do projeto",
        "category": "management",
        "description": "Ler, filtrar, criar e editar o registro diário de trabalho do projeto (aba Daily do board)",
        "tags": ["daily", "standup", "log", "project", "history", "report"],
        "filename": "relay-project-daily",
        "content": """---
description: Lê, filtra, cria e edita o Daily do projeto no Relay Local (registro diário de trabalho por dia, no board do projeto). Use quando o usuário pedir "o que foi feito no projeto ontem", "daily do projeto", "registra no daily", "resume a semana do projeto", "histórico de trabalho do projeto", "o que o time fez no dia X", ou quando um agente precisar reconstruir andamento do projeto por data.
---

# Relay — Daily do projeto (registro de trabalho por dia)

O **Daily do projeto** é um diário de trabalho: cada registro é um comentário
com **dia**, **tipo**, **texto**, autor e (opcional) minutos e card. Serve de
documento de daily e de fonte para agentes reconstruírem o andamento.

Diferente de:
- **`Comment`** → comentário de um card específico.
- **`DailyNote`** (`/api/daily/{date}`) → nota global do dia (Meu Dia), não por projeto.

## Onde aparece

- **Desktop**: Board do projeto → aba **📝 Daily**.
- **Web**: Board do projeto → aba **📝 Daily** (`/board/{id}`).
- **API**: `/api/projects/{id}/daily` (ver abaixo).

## API (base `http://127.0.0.1:9777`)

### Listar / filtrar
```bash
GET /api/projects/{projectId}/daily
    ?date=YYYY-MM-DD          # dia exato
    &dateFrom=YYYY-MM-DD      # intervalo (início)
    &dateTo=YYYY-MM-DD        # intervalo (fim)
    &kind=WORK|BLOCKER|DECISION|NOTE
    &author=nome              # busca parcial, case-insensitive
    &q=texto                  # busca no corpo
    &limit=200
```
Retorna lista ordenada do **mais recente** para o mais antigo.

```bash
# o que foi feito ontem
curl -s "http://127.0.0.1:9777/api/projects/2/daily?date=$(date -d yesterday +%F)" | jq

# semana atual, só bloqueios
curl -s "http://127.0.0.1:9777/api/projects/2/daily?dateFrom=$(date -d 'monday -7 days' +%F)&kind=BLOCKER" | jq

# busca livre
curl -s "http://127.0.0.1:9777/api/projects/2/daily?q=cashier" | jq '.[].body'
```

### Criar
```bash
curl -s -X POST "http://127.0.0.1:9777/api/projects/2/daily" \\
  -H 'Content-Type: application/json' \\
  -d '{
    "body": "Implementei a abertura de caixa e validei em loja 208",
    "date": "2026-11-08",
    "kind": "WORK",
    "author": "walter",
    "minutes": 90,
    "taskCode": "MIG-13973"
  }' | jq
```
- `date` ausente → **hoje**.
- `kind` ausente → `WORK`. Tipo inválido → `400`.
- `body` vazio/só espaços → `400`.

### Editar
```bash
curl -s -X PATCH "http://127.0.0.1:9777/api/project-daily/12" \\
  -H 'Content-Type: application/json' \\
  -d '{"body": "texto revisado", "kind": "DECISION", "minutes": 45}' | jq
```
Aceita `body`, `date`, `kind`, `author`, `minutes`, `taskCode` (todos opcionais).

### Excluir
```bash
curl -s -X DELETE "http://127.0.0.1:9777/api/project-daily/12"
```

### Resumo (para painéis e relatórios)
```bash
curl -s "http://127.0.0.1:9777/api/projects/2/daily/summary?dateFrom=2026-11-01&dateTo=2026-11-30" | jq
# { total, totalMinutes, byKind: {WORK, BLOCKER, DECISION, NOTE}, byAuthor: {...},
#   days: [{date, entries, minutes, authors}, ...] }
```

## Formato do doc de daily (vault)

O time mantém um arquivo por dia em
`vault-docs-projetos/tarefas/VERZEL/GAV/daily/YYYY-MM/DD-MM-YYYY - Daily - <tema>.md`:

```markdown
# Daily - 04/11/2026 — tema do dia

<contexto do dia>

## Itens trabalhados

### `13972` — modo de conexão do banco
- o que foi feito
- testes / commit / estado do card

## Estado da sprint

<números do board e progresso>

## Pendências

- item aberto
```

O Relay guarda o mesmo conteúdo em registros por **seção**:
`INTRO` · `ITEMS` (um por `###`) · `SPRINT` · `PENDING` (um por bullet) · `OTHER`.

### Exportar o dia no formato do vault
```bash
curl -s "http://127.0.0.1:9777/api/projects/2/daily/export?date=2026-11-04" \\
  | jq -r '.markdown' > "/tmp/04-11-2026 - Daily - tema.md"
# também devolve .filename e .monthDir prontos para salvar no vault
```

Na UI: aba **Daily** → **⬇ Exportar .md** (web baixa o arquivo; desktop abre o
salvar como).

### Importar um doc existente
```bash
# por conteúdo
curl -s -X POST "http://127.0.0.1:9777/api/projects/2/daily/import" \\
  -H 'Content-Type: application/json' \\
  -d "{\\"content\\": $(jq -Rs . < doc.md), \\"replace\\": true}" | jq

# por caminho (servidor local)
curl -s -X POST "http://127.0.0.1:9777/api/projects/2/daily/import" \\
  -H 'Content-Type: application/json' \\
  -d '{"path":"/home/wsi/.../04-11-2026 - Daily - tema.md","replace":true}' | jq
```

`replace=true` (padrão) substitui os registros daquele dia — o import é idempotente.

### Importar o histórico inteiro do vault
```bash
python3 local-client/scripts/import_daily_vault.py \\
  --dir /home/wsi/repositorios/github/vault-docs-projetos/tarefas/VERZEL/GAV/daily \\
  --project-key MIG --dry-run     # confere
# depois sem --dry-run (ou --month 2026-11 para um mês)
```

## Fluxo recomendado para o agente

1. Descobrir o projeto: `GET /api/projects` (ou usar o projeto ativo do workspace).
2. Ler o período pedido com `dateFrom`/`dateTo` (ou `date` para um dia só).
3. Se for **escrever** (criar/editar/excluir): mostrar antes o que será gravado
   (**registro + campo + valor**) e pedir confirmação — a regra de escrita do
   Relay vale também para o daily.
4. Usar `kind` com critério: `WORK` (feito), `BLOCKER` (impedimento),
   `DECISION` (decisão tomada), `NOTE` (observação).
5. Amarrar ao card quando fizer sentido: `taskCode` = `MIG-13973` etc.

## Escrevendo um resumo do período

Para relatório, combine o daily com os cards:

```bash
# 1) registros do período
curl -s "http://127.0.0.1:9777/api/projects/2/daily?dateFrom=2026-11-01&dateTo=2026-11-07" > /tmp/daily.json
# 2) estado atual do board (progresso, por pessoa, por coluna)
curl -s "http://127.0.0.1:9777/api/projects/2/board" > /tmp/board.json
# 3) resumo agregado
curl -s "http://127.0.0.1:9777/api/projects/2/daily/summary?dateFrom=2026-11-01&dateTo=2026-11-07"
```

Monte o texto por dia, separando `WORK` (entregue) de `BLOCKER` (atenção) e
`DECISION` (mudanças de rumo).

## Limites / cuidados

- **Não** confundir com o Azure DevOps nem escrever em plataforma externa: o
  daily é **local**.
- `PATCH`/`DELETE` usam `/api/project-daily/{id}` (não `/api/daily/{id}`, que é
  a nota global do Meu Dia).
- Datas sempre `YYYY-MM-DD`; formato inválido → `400`.
- Sem `project_id` válido → `404`.
""",
    },
    {
        "id": "relay-goals",
        "name": "Goals",
        "category": "management",
        "description": "Acompanhar objetivos com progresso e contagem regressiva (tag/epico/sprint)",
        "tags": ["goals", "progress", "leadership", "sprint", "epic", "metrics"],
        "filename": "relay-goals",
        "content": """---
description: Track goals with progress and countdown (tag/epic/sprint filters)
---

# Goals — Objetivos com progresso

Um goal e "entregar os cards que casam com os filtros ate a data".
Filtros (tag, epico, sprint) sao opcionais e combinaveis. O progresso
conta cards em coluna de conclusao sobre o total do filtro.

Tarefas locais (`isLocal: true`) **nao** contam no progresso do goal.

Base: `http://127.0.0.1:9777/api`

## 1. Listar goals do projeto (com progresso embutido)

```bash
curl -s http://127.0.0.1:9777/api/projects/1/goals | jq '.[] | {id, name, dueDate, tag, epic, sprint, progress}'
```

`progress` = `{total, done, pct, daysLeft}` (dias restantes; negativo = atrasado).

## 2. Criar goal

```bash
# Ex.: entregar os cards com a tag onda-1 ate o fim do mes
curl -X POST http://127.0.0.1:9777/api/projects/1/goals \\
  -H 'Content-Type: application/json' \\
  -d '{"name":"Entregar onda-1","dueDate":"2026-12-31","tag":"onda-1"}'
```

Combinacoes uteis:
- por epico: `{"name":"...","epicId":3}`
- por sprint: `{"name":"...","sprintId":2}`
- combinados: tag + epicId + sprintId

## 3. Detalhe e atualizacao

```bash
curl http://127.0.0.1:9777/api/goals/5
curl -X PATCH http://127.0.0.1:9777/api/goals/5 \\
  -H 'Content-Type: application/json' -d '{"tag":"onda-2"}'
curl -X DELETE http://127.0.0.1:9777/api/goals/5
```

## 4. Exportar as metricas do projeto em PDF

```bash
# mesmo conteudo da aba Metricas do board (progresso, colunas, pessoas,
# modulos, prioridades e daily), pronto para enviar a lideranca
curl -s -o metricas.pdf \\
  "http://127.0.0.1:9777/api/projects/1/metrics/export.pdf"
# Content-Disposition: attachment; filename="metricas-<KEY>-<data>.pdf"
```

## 5. Ler o progresso como lider

- `pct` < 100 com `daysLeft` <= 7 → risco, verificar bloqueios no board
- `daysLeft` negativo → atrasado; renegociar escopo ou data
- Comparar `done/total` entre goals para priorizar a sprint

## OpenCode tools (se disponiveis)

- `relay_listGoals` — listar com progresso
- `relay_createGoal` — criar
- `relay_goalProgress` — detalhe + progresso
""",
    },
    {
        "id": "relay-members",
        "name": "Team Members",
        "category": "management",
        "description": "Gerenciar responsaveis do projeto, atribuir cards e ver metricas por pessoa",
        "tags": ["members", "assignee", "team", "metrics", "leadership"],
        "filename": "relay-members",
        "content": """---
description: Manage project assignees, assign cards and view per-person metrics
---

# Team Members — Responsaveis do projeto

Lista de quem pode receber cards. Alimenta a atribuicao no card, o filtro
do board ("Responsavel") e as metricas por pessoa.

Base: `http://127.0.0.1:9777/api`

## 1. Listar (com metricas: total/developed/developedPct/done/pct/overdue)

```bash
curl -s http://127.0.0.1:9777/api/projects/1/members | jq '.'
```

## 2. Adicionar / remover

```bash
curl -X POST http://127.0.0.1:9777/api/projects/1/members \\
  -H 'Content-Type: application/json' -d '{"name":"Walter"}'
curl -X DELETE http://127.0.0.1:9777/api/members/3
```

Nomes duplicados (ignorando caixa) retornam o membro existente.
Remover nao apaga os cards — eles mantem o nome em `assignee`.

## 3. Atribuir card (cria o membro se nao existir)

```bash
curl -X PATCH http://127.0.0.1:9777/api/tasks/KEY-1 \\
  -H 'Content-Type: application/json' -d '{"assignee":"Walter"}'
```

## 4. Metricas como lider

- `pct` baixo com `total` alto → sobrecarga; redistribuir
- `overdue` > 0 → cards vencidos em aberto; cobrar desbloqueio
- `developed`/`developedPct` = dev concluido (Dev Box ou depois); `done` = aceito.
  Comparar `developed` entre membros no dia a dia; `done` no fechamento

## 5. Report semanal do time (entregas + servico)

Numero vem do board; a leitura do lider vem das anotacoes (`TeamNote`).

```bash
curl -s "http://127.0.0.1:9777/api/projects/1/team/weekly?week=2026-11-04" | jq '{
  week, summary,
  membros: [.members[] | {name, deliveredCount, open, overdue, reviews, byColumn, note}]
}'
# salvar a anotacao da semana (weekStart normaliza para segunda)
curl -s -X PUT http://127.0.0.1:9777/api/projects/1/team/notes \\
  -H 'Content-Type: application/json' \\
  -d '{"member":"Ana","weekStart":"2026-11-04","highlights":"fechou config","service":"revisou 2 PRs","attention":"PR sem revisor","nextStep":"cashier O1"}' | jq
# relatorio em markdown (nominal ou anonimizado)
curl -s -o report.md "http://127.0.0.1:9777/api/projects/1/team/weekly/export?week=2026-11-02"
curl -s -o report-anon.md "http://127.0.0.1:9777/api/projects/1/team/weekly/export?week=2026-11-02&anonymized=1"
```

- `week` aceita qualquer dia; normaliza para **segunda→domingo**
- `delivered[]` so conta `done_at` real; card importado (concluido na carga)
  vira `legacyDone` e nao entra como entrega da semana
- `note` tem `highlights` (como esta trabalhando), `service` (reviews/infra/
  suporte), `attention` e `nextStep`
- o markdown segue o formato `lideranca/gestao/acompanhamento-semanal-equipe-*.md`
  (secoes: resumo, por membro, distribuicao de carga)
- versao anonimizada troca nomes por `Pessoa A/B/C` — use para apresentacao ampla

## OpenCode tools (se disponiveis)

- `relay_listMembers` — listar com metricas
- `relay_addMember` — adicionar
- `relay_assignTask` — atribuir card
""",
    },
]

CATEGORIES = {
    "setup": "Setup",
    "agent": "Agente",
    "workflow": "Fluxo de Trabalho",
    "management": "Gestão",
}
