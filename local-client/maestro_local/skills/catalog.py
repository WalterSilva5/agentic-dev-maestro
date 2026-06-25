SKILLS = [
    {
        "id": "run",
        "name": "Run Maestro Local",
        "category": "setup",
        "description": "Iniciar a aplicacao desktop (GUI + API)",
        "tags": ["setup", "launch"],
        "filename": "run",
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
        "id": "api-agent",
        "name": "API Agent Usage",
        "category": "agent",
        "description": "Interagir com a API REST como agente de IA",
        "tags": ["api", "agent", "rest"],
        "filename": "api-agent",
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
        "id": "task-workflow",
        "name": "Task Workflow",
        "category": "workflow",
        "description": "Fluxo completo de trabalho com tarefas: pegar task, implementar, mover, documentar",
        "tags": ["workflow", "task", "development"],
        "filename": "task-workflow",
        "content": """---
description: Complete task workflow - pick, implement, move, document
---

# Task Workflow

Fluxo padrao para trabalhar com uma tarefa no Maestro Local.

## 1. Buscar proxima tarefa disponivel

```bash
# Listar tarefas no backlog ou "A fazer"
curl -s http://127.0.0.1:9777/api/tasks?status=Backlog | jq '.[0]'
curl -s http://127.0.0.1:9777/api/tasks?status=A+fazer | jq '.[0]'
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

## 4. Registrar progresso via comentarios

```bash
curl -X POST http://127.0.0.1:9777/api/comments \\
  -H 'Content-Type: application/json' \\
  -d '{"taskId":ID,"body":"Progresso: implementado modulo X","type":"COMMENT"}'
```

Tipos de comentario:
- `COMMENT` — comentario geral
- `CODE_REVIEW` — revisao de codigo
- `COMMIT_REF` — referencia a commit
- `DEPLOY_LOG` — log de deploy

## 5. Atualizar checklist (Definition of Done)

```bash
# Listar checklist
curl -s http://127.0.0.1:9777/api/tasks/{CODE} | jq '.checklist'

# Marcar item como concluido
curl -X PATCH http://127.0.0.1:9777/api/tasks/checklist/{ITEM_ID}/toggle
```

## 6. Mover para "Revisao" ou "Concluido"

```bash
curl -X POST http://127.0.0.1:9777/api/tasks/{CODE}/move \\
  -H 'Content-Type: application/json' \\
  -d '{"columnId": REVIEW_COLUMN_ID}'
```
""",
    },
    {
        "id": "project-setup",
        "name": "Project Setup",
        "category": "setup",
        "description": "Criar e configurar um novo projeto com labels, tarefas iniciais e checklist",
        "tags": ["setup", "project", "bootstrap"],
        "filename": "project-setup",
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
        "id": "sprint-planning",
        "name": "Sprint Planning",
        "category": "workflow",
        "description": "Planejar sprint: analisar metricas, priorizar backlog, estimar tarefas",
        "tags": ["sprint", "planning", "metrics"],
        "filename": "sprint-planning",
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
        "id": "code-review-log",
        "name": "Code Review Log",
        "category": "workflow",
        "description": "Registrar resultados de code review em tarefas com comentarios tipados",
        "tags": ["review", "code", "quality"],
        "filename": "code-review-log",
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
        "id": "bug-triage",
        "name": "Bug Triage",
        "category": "workflow",
        "description": "Triagem de bugs: criar, classificar, priorizar e documentar",
        "tags": ["bug", "triage", "quality"],
        "filename": "bug-triage",
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
        "id": "daily-standup",
        "name": "Daily Standup",
        "category": "workflow",
        "description": "Gerar resumo para daily standup: o que foi feito, o que esta em andamento, bloqueios",
        "tags": ["daily", "standup", "report"],
        "filename": "daily-standup",
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
        "id": "tech-debt-tracker",
        "name": "Tech Debt Tracker",
        "category": "management",
        "description": "Rastrear e gerenciar divida tecnica com tarefas tipadas e metricas",
        "tags": ["tech-debt", "management", "quality"],
        "filename": "tech-debt-tracker",
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
        "id": "documentation-writer",
        "name": "Documentation Writer",
        "category": "management",
        "description": "Criar e gerenciar documentos tecnicos vinculados a projetos e tarefas",
        "tags": ["docs", "documentation", "writing"],
        "filename": "documentation-writer",
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
]

CATEGORIES = {
    "setup": "Setup",
    "agent": "Agente",
    "workflow": "Fluxo de Trabalho",
    "management": "Gestao",
}
