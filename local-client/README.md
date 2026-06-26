# Maestro Local

Cliente desktop do Agentic Dev Maestro. Organiza tarefas, diario de trabalho e estudos, com API REST embutida para integracao com agentes de IA.

## Instalacao e execucao

### Rapido (recomendado)

```bash
./install.sh    # cria venv, instala deps, valida
./run.sh        # executa
```

### Manual

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m maestro_local
```

### Opcoes

```bash
./run.sh --port 8888    # porta customizada (padrao: 9777)
```

### Entry point global

Apos `pip install -e .`, o comando `maestro` fica disponivel no PATH do venv:

```bash
maestro              # porta padrao
maestro --port 8888  # porta customizada
```

## O que a aplicacao faz

Ao iniciar, o Maestro abre:
1. **GUI desktop** (PySide6/Qt 6) — interface grafica com 9 telas
2. **API REST** (FastAPI/uvicorn) — `http://127.0.0.1:9777/api` em thread daemon

A tela inicial e **Meu Dia**, que funciona como home da aplicacao.

## Telas

### Meu Dia (Alt+2) — home

Tela principal do dia de trabalho:

- **Obsidian Vault**: selecionar vault por projeto/workspace, sincronizar notas e tarefas com o Obsidian. Sync automatico a cada 5 minutos
- **Notas do dia**: editor markdown com template pre-configurado, preview renderizado, botao para inserir template padrao (Foco do Dia, Tarefas, Blockers, Notas Tecnicas)
- **Gerar Relatorio**: gera relatorio automatico com lista de tarefas trabalhadas, atividades do dia e resumo
- **Dica IA**: ao lado do relatorio gerado, botao com prompt sugerido para pedir a um agente de IA que resuma o dia usando a skill `maestro-daily-report`
- **Atividade do dia**: timeline com todas as acoes do dia (tasks criadas, movidas, comentadas)
- **Backup do Banco**: exportar copia do banco SQLite

### Dashboard (Alt+1)

Visao geral do workspace:

- **Cards de resumo**: tarefas ativas, concluidas (7 dias), vencidas, em progresso
- **Tarefas vencidas**: lista clicavel que abre o detalhe da tarefa
- **Atividade recente**: timeline das ultimas 15 acoes agrupadas por dia
- **Projetos**: progresso de cada projeto com barra e contagem por coluna

### Estudos (Alt+3)

Modulo de aprendizado:

- **Planos de estudo**: criar planos com nome, categoria (Linguagem, Framework, Certificacao, Conceito, Curso, Livro) e status (Nao Iniciado, Em Progresso, Concluido, Pausado)
- **Topicos**: adicionar topicos com peso e estimativa de horas. Marcar como concluido
- **Roadmap visual**: barra de progresso calculada pelo peso dos topicos concluidos
- **Sessoes de estudo**: registrar tempo de estudo com notas e nivel de confianca (1-5)
- **Estatisticas**: horas totais, sessoes por semana, planos ativos

### Board Kanban (Alt+4)

Board de tarefas por projeto:

- **Colunas**: customizaveis por projeto (ex: Backlog, A Fazer, Fazendo, Revisao, Concluido)
- **Drag-and-drop**: arrastar cards entre colunas
- **Quick-move**: botao para avancar tarefa para proxima coluna sem arrastar
- **Filtros**: por tipo (Feature, Bug, Tech Debt, Improvement, Chore), prioridade (Low, Medium, High, Urgent), responsavel e label
- **WIP limits**: limite de tarefas por coluna
- **Cards**: mostram tipo, prioridade, labels, due date, assignee, indicador de bloqueio e checklist progress
- **Task detail**: dialog completo com titulo, descricao, tipo, prioridade, assignee, due date, labels, checklist (Definition of Done), dependencias, comentarios com markdown

### Projetos (Alt+5)

- Criar projetos com nome, chave unica (ex: DEMO, PROJ) e descricao
- Cada projeto gera automaticamente colunas padrao no board
- Visao de lista com link para o board

### Labels (Alt+6)

- Criar labels com nome e cor (paleta de 12 cores)
- Aplicar labels em tarefas para categorizar e filtrar
- Labels compartilhadas entre projetos do mesmo workspace

### Metricas (Alt+7)

Dashboard analitico:

- **Cards**: total de tarefas, concluidas (7 e 30 dias), lead time medio, cycle time
- **Throughput semanal**: grafico de barras das ultimas 8 semanas
- **Por tipo**: breakdown Feature/Bug/Tech Debt/Improvement/Chore com percentual
- **Por prioridade**: breakdown Low/Medium/High/Urgent com percentual
- **Por projeto**: progresso de cada projeto com barra

### Skills (Alt+8)

Biblioteca de skills para agentes de IA:

- **11 skills** com prefixo `maestro-` organizadas por categoria (Setup, Agente, Fluxo de Trabalho, Planejamento, Qualidade, Registro)
- **Instalar**: um clique instala o arquivo SKILL.md em `.claude/skills/` do projeto alvo
- **Instalar todas**: botao para instalar todas as skills de uma vez
- **Preview**: ver o conteudo da skill antes de instalar
- **Diretorio destino**: selecionar o projeto onde instalar as skills

### Instrucoes (Alt+9)

Guia de uso com explicacoes de cada tela e fluxo de trabalho.

## Recursos gerais

| Recurso | Descricao |
|---|---|
| **Tema dark/light** | Toggle na sidebar, aplica em todas as telas |
| **Pomodoro** | Timer de 25 min na sidebar com play/pause e reset |
| **Busca global** | `Ctrl+K` abre busca por titulo ou codigo de tarefa |
| **Workspaces** | Isolamento completo com banco separado, emoji, cor e descricao customizaveis |
| **Obsidian sync** | Auto-sync a cada 5 min, vault configuravel por workspace/projeto |
| **Backup** | Exportar banco SQLite a qualquer momento |
| **Atalhos** | `Alt+1` a `Alt+9` para navegar entre telas, `Ctrl+K` para busca |

## API REST

A API roda em `http://127.0.0.1:9777/api` sem autenticacao. Todos os endpoints retornam JSON.

### Endpoints

| Recurso | Metodo | Endpoint | Descricao |
|---|---|---|---|
| Health | GET | `/api/health` | Status da API |
| Projetos | POST | `/api/projects` | Criar projeto |
| Projetos | GET | `/api/projects` | Listar projetos |
| Projetos | GET | `/api/projects/metrics` | Metricas por projeto |
| Projetos | GET | `/api/projects/{id}/board` | Board completo do projeto |
| Tarefas | POST | `/api/tasks` | Criar tarefa |
| Tarefas | GET | `/api/tasks` | Listar tarefas (filtros: project_id, column_id, type, priority) |
| Tarefas | GET | `/api/tasks/{code}` | Detalhe da tarefa por codigo (ex: DEMO-1) |
| Tarefas | PATCH | `/api/tasks/{code}` | Atualizar tarefa |
| Tarefas | DELETE | `/api/tasks/{code}` | Soft-delete da tarefa |
| Tarefas | POST | `/api/tasks/{code}/move` | Mover para coluna (body: {column_id}) |
| Checklist | POST | `/api/tasks/{code}/checklist` | Adicionar item de checklist |
| Checklist | PATCH | `/api/tasks/checklist/{id}/toggle` | Toggle checked |
| Checklist | DELETE | `/api/tasks/checklist/{id}` | Remover item |
| Dependencias | POST | `/api/tasks/{code}/dependencies` | Adicionar dependencia |
| Dependencias | DELETE | `/api/tasks/{code}/dependencies/{id}` | Remover dependencia |
| Context | GET | `/api/tasks/{code}/context` | Contexto completo da tarefa |
| Context | GET | `/api/tasks/{code}/flow` | Fluxo de trabalho da tarefa |
| Labels | POST | `/api/labels` | Criar label |
| Labels | GET | `/api/labels` | Listar labels |
| Labels | DELETE | `/api/labels/{id}` | Remover label |
| Labels | POST | `/api/labels/{id}/tasks/{task_id}` | Aplicar label em tarefa |
| Labels | DELETE | `/api/labels/{id}/tasks/{task_id}` | Remover label de tarefa |
| Comentarios | POST | `/api/comments` | Criar comentario |
| Comentarios | GET | `/api/comments` | Listar comentarios (filtro: task_id) |
| Comentarios | PATCH | `/api/comments/{id}` | Editar comentario |
| Comentarios | DELETE | `/api/comments/{id}` | Remover comentario |
| Documentos | POST | `/api/documents` | Criar documento |
| Documentos | GET | `/api/documents` | Listar documentos |
| Documentos | PUT | `/api/documents/{id}` | Atualizar documento |
| Documentos | DELETE | `/api/documents/{id}` | Remover documento |
| Atividade | GET | `/api/activity` | Log de atividades |
| Diario | GET | `/api/daily/{date}` | Nota do dia (YYYY-MM-DD) |
| Diario | POST | `/api/daily/{date}` | Criar/atualizar nota do dia |
| Diario | PATCH | `/api/daily/{date}/report` | Append ao relatorio do dia |
| Estudos | POST | `/api/study/plans` | Criar plano de estudo |
| Estudos | GET | `/api/study/plans` | Listar planos |
| Estudos | GET | `/api/study/plans/{id}` | Detalhe do plano |
| Estudos | PATCH | `/api/study/plans/{id}` | Atualizar plano |
| Estudos | DELETE | `/api/study/plans/{id}` | Remover plano |
| Topicos | POST | `/api/study/plans/{id}/topics` | Adicionar topico |
| Topicos | GET | `/api/study/plans/{id}/topics` | Listar topicos |
| Topicos | PATCH | `/api/study/topics/{id}` | Atualizar topico |
| Topicos | DELETE | `/api/study/topics/{id}` | Remover topico |
| Sessoes | POST | `/api/study/sessions` | Registrar sessao de estudo |
| Sessoes | GET | `/api/study/sessions` | Listar sessoes (filtro: date) |
| Stats | GET | `/api/study/stats` | Estatisticas de estudo |

### Exemplo: criar tarefa via curl

```bash
# Criar projeto
curl -X POST http://127.0.0.1:9777/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Meu Projeto", "key": "MP"}'

# Criar tarefa
curl -X POST http://127.0.0.1:9777/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Implementar login", "project_id": 1, "type": "FEATURE", "priority": "HIGH"}'

# Mover tarefa
curl -X POST http://127.0.0.1:9777/api/tasks/MP-1/move \
  -H "Content-Type: application/json" \
  -d '{"column_id": 2}'
```

## Skills para agentes de IA

| Skill | Categoria | O que faz |
|---|---|---|
| `maestro-run` | Setup | Iniciar a aplicacao (GUI + API) |
| `maestro-api-agent` | Agente | Ensina o agente a interagir com a API REST |
| `maestro-task-workflow` | Fluxo | Fluxo completo: pegar task, implementar, mover, documentar |
| `maestro-project-setup` | Setup | Criar projeto com colunas e labels padrao |
| `maestro-sprint-planning` | Planejamento | Planejar sprint com estimativas e priorizacao |
| `maestro-code-review-log` | Qualidade | Registrar code reviews como comentarios |
| `maestro-bug-triage` | Qualidade | Triagem de bugs com prioridade e reproducao |
| `maestro-daily-standup` | Registro | Gerar relatorio de standup automatico |
| `maestro-tech-debt-tracker` | Qualidade | Registrar e priorizar divida tecnica |
| `maestro-documentation-writer` | Registro | Gerar documentacao a partir do codigo |
| `maestro-daily-report` | Registro | Relatorio diario com notas, atividade e resumo em bullet list |

## Tipos de tarefa

| Tipo | Uso |
|---|---|
| `FEATURE` | Nova funcionalidade |
| `BUG` | Correcao de bug |
| `TECH_DEBT` | Divida tecnica |
| `IMPROVEMENT` | Melhoria em funcionalidade existente |
| `CHORE` | Tarefa operacional |

## Prioridades

| Prioridade | Nivel |
|---|---|
| `LOW` | Baixa |
| `MEDIUM` | Media |
| `HIGH` | Alta |
| `URGENT` | Urgente |

## Banco de dados

SQLite local com isolamento por workspace:

```
~/.maestro-local/
├── config.json                     # Workspaces, vaults, tema
└── workspaces/
    ├── default/maestro.db          # Workspace padrao
    └── {workspace-id}/maestro.db   # Workspaces adicionais
```

O banco e criado automaticamente na primeira execucao. Cada workspace tem seu proprio arquivo, garantindo isolamento total dos dados.

## Estrutura do codigo

```
maestro_local/
├── __main__.py              # Entry point: init_db -> start_api -> QApplication
├── config.py                # Config JSON + workspace management
├── db/
│   └── models.py            # SQLAlchemy models + switch_db()
├── api/
│   ├── app.py               # FastAPI endpoints (todos os recursos)
│   └── server.py            # Uvicorn runner em thread daemon
├── gui/
│   ├── theme.py             # ThemeColors dataclass + dark/light + stylesheet
│   ├── main_window.py       # MainWindow + sidebar + pomodoro + workspace selector
│   ├── workspace_selector.py # Seletor de workspace com emoji/cor/descricao
│   └── views/
│       ├── daily_view.py        # Meu Dia + Obsidian sync + relatorio
│       ├── dashboard_view.py    # Dashboard com resumo e atividade
│       ├── study_view.py        # Planos de estudo + topicos + sessoes
│       ├── board_view.py        # Kanban board + TaskCard + filtros
│       ├── task_detail_dialog.py # Dialog completo de tarefa
│       ├── projects_view.py     # Lista/criacao de projetos
│       ├── labels_view.py       # CRUD de labels com paleta
│       ├── metrics_view.py      # Dashboard de metricas
│       ├── skills_view.py       # Skills para agentes de IA
│       └── guide_view.py        # Instrucoes de uso
└── skills/
    └── catalog.py           # Catalogo de 11 skills com conteudo SKILL.md
```

## Requisitos

- Python 3.10+
- Qt 6 (instalado automaticamente com PySide6)
- Linux, macOS ou Windows
