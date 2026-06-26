SKILLS = [
    {
        "id": "maestro-run",
        "name": "Run Maestro Local",
        "category": "setup",
        "description": "Iniciar a aplicacao desktop (GUI + API)",
        "tags": ["setup", "launch"],
        "filename": "maestro-run",
        "content": """---
description: Run the Maestro Local desktop app (GUI + API)
---

# Run Maestro Local

```bash
cd {project_dir}
source .venv/bin/activate
python -m maestro_local
```

API fica disponivel em `http://127.0.0.1:9777/api`.

Para testar a API:
```bash
curl http://127.0.0.1:9777/api/health
```
""",
    },
    {
        "id": "maestro-api-agent",
        "name": "API Agent Usage",
        "category": "agent",
        "description": "Interagir com a API REST como agente de IA",
        "tags": ["api", "agent", "rest"],
        "filename": "maestro-api-agent",
        "content": """---
description: Interact with Maestro Local API as an AI agent
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
""",
    },
    {
        "id": "maestro-task-workflow",
        "name": "Task Workflow",
        "category": "workflow",
        "description": "Fluxo completo de trabalho com tarefas: pegar task, implementar, mover, documentar",
        "tags": ["workflow", "task", "development"],
        "filename": "maestro-task-workflow",
        "content": """---
description: Complete task workflow - pick, implement, move, document
---

# Task Workflow

Fluxo padrao para trabalhar com uma tarefa no Maestro Local.

## REGRAS FUNDAMENTAIS

### NUNCA fazer commits ou pushs sem autorizacao explicita

O agente **NUNCA** deve executar `git commit`, `git push`, ou qualquer
operacao de versionamento por conta propria. Commits e pushs so devem
ser feitos quando o desenvolvedor **explicitamente** pedir.

O papel do agente e:
1. **Implementar** o codigo da tarefa
2. **Documentar** o que foi feito (comentarios, code review, docs)
3. **Informar o desenvolvedor** sobre o estado e proximo passo
4. **Aguardar** a decisao do dev sobre commit/push

Ao terminar uma implementacao, o agente deve:
- Criar o code review como comentario na tarefa
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

## 7. Informar o desenvolvedor

Apos mover para Revisao, o agente deve informar o desenvolvedor:

- Resumo do que foi implementado
- Lista de arquivos modificados
- O que o dev precisa testar/validar
- Lembrar que commits e pushs sao responsabilidade do dev

**O agente NAO faz commit. O agente NAO faz push. O agente documenta e informa.**
""",
    },
    {
        "id": "maestro-project-setup",
        "name": "Project Setup",
        "category": "setup",
        "description": "Criar e configurar um novo projeto com labels, tarefas iniciais e checklist",
        "tags": ["setup", "project", "bootstrap"],
        "filename": "maestro-project-setup",
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

Colunas criadas automaticamente: Backlog, A fazer, Fazendo, Revisao, Concluido.

## 2. Criar labels

```bash
for label in '{"name":"frontend","color":"#4C6EF5"}' '{"name":"backend","color":"#2F9E44"}' '{"name":"infra","color":"#E8590C"}' '{"name":"docs","color":"#868E96"}'; do
  curl -X POST http://127.0.0.1:9777/api/labels \\
    -H 'Content-Type: application/json' -d "$label"
done
```

## 3. Criar tarefas iniciais

```bash
curl -X POST http://127.0.0.1:9777/api/tasks \\
  -H 'Content-Type: application/json' \\
  -d '{"projectId":1,"title":"Setup do repositorio","type":"CHORE","priority":"HIGH"}'
```

## 4. Adicionar checklist (Definition of Done)

```bash
curl -X POST http://127.0.0.1:9777/api/tasks/KEY-1/checklist \\
  -H 'Content-Type: application/json' -d '{"title":"Testes passando"}'

curl -X POST http://127.0.0.1:9777/api/tasks/KEY-1/checklist \\
  -H 'Content-Type: application/json' -d '{"title":"Code review aprovado"}'

curl -X POST http://127.0.0.1:9777/api/tasks/KEY-1/checklist \\
  -H 'Content-Type: application/json' -d '{"title":"Documentacao atualizada"}'
```

## 5. Adicionar dependencias

```bash
# KEY-2 so pode comecar depois de KEY-1
curl -X POST http://127.0.0.1:9777/api/tasks/KEY-2/dependencies \\
  -H 'Content-Type: application/json' -d '{"blockerCode":"KEY-1"}'
```
""",
    },
    {
        "id": "maestro-sprint-planning",
        "name": "Sprint Planning",
        "category": "workflow",
        "description": "Planejar sprint: analisar metricas, priorizar backlog, estimar tarefas",
        "tags": ["sprint", "planning", "metrics"],
        "filename": "maestro-sprint-planning",
        "content": """---
description: Sprint planning - analyze metrics, prioritize backlog, estimate tasks
---

# Sprint Planning

Auxiliar no planejamento de sprint usando dados do Maestro.

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
        "id": "maestro-code-review-log",
        "name": "Code Review Log",
        "category": "workflow",
        "description": "Registrar resultados de code review em tarefas com comentarios tipados",
        "tags": ["review", "code", "quality"],
        "filename": "maestro-code-review-log",
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
        "id": "maestro-bug-triage",
        "name": "Bug Triage",
        "category": "workflow",
        "description": "Triagem de bugs: criar, classificar, priorizar e documentar",
        "tags": ["bug", "triage", "quality"],
        "filename": "maestro-bug-triage",
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
        "id": "maestro-daily-standup",
        "name": "Daily Standup",
        "category": "workflow",
        "description": "Gerar resumo para daily standup: o que foi feito, o que esta em andamento, bloqueios",
        "tags": ["daily", "standup", "report"],
        "filename": "maestro-daily-standup",
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

## 5. Metricas do dia

```bash
curl -s http://127.0.0.1:9777/api/projects/metrics | \\
  jq '{completedLast7d: .summary.completedLast7d, avgLeadTimeHours: .summary.avgLeadTimeHours}'
```
""",
    },
    {
        "id": "maestro-tech-debt-tracker",
        "name": "Tech Debt Tracker",
        "category": "management",
        "description": "Rastrear e gerenciar divida tecnica com tarefas tipadas e metricas",
        "tags": ["tech-debt", "management", "quality"],
        "filename": "maestro-tech-debt-tracker",
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
        "id": "maestro-documentation-writer",
        "name": "Documentation Writer",
        "category": "management",
        "description": "Criar e gerenciar documentos tecnicos vinculados a projetos e tarefas",
        "tags": ["docs", "documentation", "writing"],
        "filename": "maestro-documentation-writer",
        "content": """---
description: Create and manage technical documents linked to projects and tasks
---

# Documentation Writer

Gerenciar documentos tecnicos no Maestro Local.

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
        "id": "maestro-daily-report",
        "name": "Daily Report",
        "category": "workflow",
        "description": "Gerar relatorio diario: criar nota, registrar atividades e gerar resumo via API",
        "tags": ["daily", "report", "notes", "tracking"],
        "filename": "maestro-daily-report",
        "content": """---
description: Generate daily report - create notes, track activity, generate summary via API
---

# Daily Report

Fluxo para o agente criar e gerar o relatorio diario do usuario.

## IMPORTANTE: A nota do dia e o conteudo PRINCIPAL do relatorio

O relatorio e gerado a partir da nota do dia (body da DailyNote). O conteudo
da nota aparece INTEIRO no topo do relatorio, preservando todas as secoes.

As atividades do board e timeline sao COMPLEMENTARES — aparecem abaixo da
nota do dia como "Tarefas do Board" e "Timeline de Atividades".

## Template de nota diaria

O template padrao e simples — apenas checklist:

```markdown
## Foco do Dia
- [ ] ...

## Bloqueios
- ...

## Notas
- ...
```

## 1. Verificar nota existente do dia

```bash
curl -s http://127.0.0.1:9777/api/daily/2026-06-25
```

Se a nota ja existe, leia o body para entender o contexto do dia.

## 2. Criar nota do dia (se nao existe)

```bash
curl -X PUT http://127.0.0.1:9777/api/daily/2026-06-25 \\
  -H 'Content-Type: application/json' \\
  -d '{"body":"## Foco do Dia\\n- [ ] Implementar modulo X\\n..."}'
```

## 3. Atualizar nota do dia

```bash
curl -X PATCH http://127.0.0.1:9777/api/daily/2026-06-25 \\
  -H 'Content-Type: application/json' \\
  -d '{"body":"## Foco do Dia\\n- [x] Implementar modulo X\\n- [ ] Modulo Y\\n..."}'
```

Use PATCH para atualizar secoes especificas sem perder o que ja existe.

## 4. Ver atividade do dia (complementar)

```bash
curl -s http://127.0.0.1:9777/api/daily/2026-06-25/activity
```

Retorna tarefas que tiveram atividade no board.
Use para ENRIQUECER a nota — adicione itens nos checkpoints.

## 5. Gerar relatorio base do dia

```bash
curl -X POST http://127.0.0.1:9777/api/daily/2026-06-25/report
```

O relatorio inclui:
1. Conteudo completo da nota do dia (topo)
2. Tarefas do board que tiveram atividade
3. Timeline de atividades
4. Resumo automatico

## 6. Adicionar analise ao relatorio

```bash
curl -X PATCH http://127.0.0.1:9777/api/daily/2026-06-25/report \\
  -H 'Content-Type: application/json' \\
  -d '{"content":"## Analise\\n- ..."}'
```

## Fluxo recomendado

1. Verificar se ja existe nota (`GET /api/daily/{date}`)
2. Se existe: ler o body
3. Se nao existe: criar com template (`PUT /api/daily/{date}`)
4. Verificar atividade do board (`GET /api/daily/{date}/activity`)
5. Atualizar nota com informacoes novas (`PATCH /api/daily/{date}`)
6. Gerar relatorio quando solicitado (`POST /api/daily/{date}/report`)
7. **Gerar resumo final** (ver secao abaixo)

## 7. Resumo final para registro de trabalho

Ao final do fluxo, SEMPRE gere um resumo simples para registro de trabalho.
O resumo deve ser uma bullet list direta, sem codigo, sem detalhes tecnicos,
sem explicacoes longas — apenas o que foi feito no dia.

### Formato obrigatorio

```markdown
## Resumo do dia — YYYY-MM-DD

- Tarefa/atividade descrita de forma simples e curta
- Outra tarefa ou atividade
- ...
```

### Exemplo

```markdown
## Resumo do dia — 2026-06-26

- Implementacao do modulo de notificacoes
- Correcao de bug no login com Google
- Revisao de PR do fluxo de pagamento
- Reuniao de alinhamento com o time de produto
- Atualizacao da documentacao da API
```

### Regras do resumo

- Uma linha por item, comecando com `-`
- Linguagem simples e direta (sem jargao tecnico desnecessario)
- NAO incluir: trechos de codigo, nomes de arquivos, hashes de commit, stack traces
- NAO incluir: detalhes de implementacao ("adicionei campo X na tabela Y")
- SIM incluir: o QUE foi feito em alto nivel ("implementacao do modulo de relatorios")
- Manter entre 3 e 15 itens — agrupar atividades menores relacionadas
- Usar verbos no passado ou infinitivo ("Implementacao de...", "Correcao de...")

O resumo deve ser exibido ao usuario no final da conversa E salvo na nota do dia
via `PATCH /api/daily/{date}` — adicionado ao final do body existente.

## Dicas

- A nota do dia e a FONTE PRINCIPAL do relatorio
- O relatorio preserva o conteudo da nota inteiro no topo
- Use `GET /api/daily/{date}/activity` para complementar
- A data sempre no formato ISO: YYYY-MM-DD
- O resumo final e obrigatorio — nao encerre sem gera-lo
""",
    },
]

CATEGORIES = {
    "setup": "Setup",
    "agent": "Agente",
    "workflow": "Fluxo de Trabalho",
    "management": "Gestao",
}
