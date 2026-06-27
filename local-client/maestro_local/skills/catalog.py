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
        "id": "maestro-context-loader",
        "name": "Context Loader",
        "category": "agent",
        "description": "Carregar contexto completo dos projetos, boards e tarefas para continuar de onde parou",
        "tags": ["context", "board", "project", "resume", "continuidade"],
        "filename": "maestro-context-loader",
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

Com esse mapa, o agente pode:
- Continuar uma tarefa em andamento de onde parou
- Pegar a proxima tarefa mais prioritaria
- Desbloquear tarefas pendentes
- Reportar o estado atual ao dev
- Revisar o que foi feito antes de avancar

## DICA

Execute esta skill sempre que iniciar uma nova conversa ou
quando mudar de workspace. O contexto muda frequentemente
e o agente deve estar sempre atualizado.

Para revisao de contexto rapida, use apenas os passos 8 e 9
(historico da tarefa + changelog do projeto).
""",
    },
]

CATEGORIES = {
    "setup": "Setup",
    "agent": "Agente",
    "workflow": "Fluxo de Trabalho",
    "management": "Gestão",
}
