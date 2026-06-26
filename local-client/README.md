# Maestro Local

Cliente desktop do Agentic Dev Maestro. Organiza tarefas, diário de trabalho e estudos, com API REST embutida para integração com agentes de IA.

## Instalação e execução

### Rápido (recomendado)

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

### Opções

```bash
./run.sh --port 8888    # porta customizada (padrão: 9777)
```

### Entry point global

Após `pip install -e .`, o comando `maestro` fica disponível no PATH do venv:

```bash
maestro              # porta padrão
maestro --port 8888  # porta customizada
```

## O que a aplicação faz

Ao iniciar, o Maestro abre:
1. **GUI desktop** (PySide6/Qt 6) — interface gráfica com 9 telas
2. **API REST** (FastAPI/uvicorn) — `http://127.0.0.1:9777/api` em thread daemon

A tela inicial é **Meu Dia**, que funciona como home da aplicação.

## Telas

### Meu Dia (Alt+2) — home

Tela principal do dia de trabalho:

- **Obsidian Vault**: selecionar vault por projeto/workspace, sincronizar notas e tarefas com o Obsidian. Sync automático a cada 5 minutos
- **Notas do dia**: editor markdown com template pre-configurado, preview renderizado, botão para inserir template padrão (Foco do Dia, Tarefas, Blockers, Notas Técnicas)
- **Gerar Relatório**: gera relatório automático com lista de tarefas trabalhadas, atividades do dia e resumo
- **Dica IA**: ao lado do relatório gerado, botão com prompt sugerido para pedir a um agente de IA que resuma o dia usando a skill `maestro-daily-report`
- **Atividade do dia**: timeline com todas as ações do dia (tasks criadas, movidas, comentadas)
- **Backup do Banco**: exportar cópia do banco SQLite

### Dashboard (Alt+1)

Visão geral do workspace:

- **Cards de resumo**: tarefas ativas, concluídas (7 dias), vencidas, em progresso
- **Tarefas vencidas**: lista clicável que abre o detalhe da tarefa
- **Atividade recente**: timeline das últimas 15 ações agrupadas por dia
- **Projetos**: progresso de cada projeto com barra e contagem por coluna

### Estudos (Alt+3)

Módulo de aprendizado:

- **Planos de estudo**: criar planos com nome, categoria (Linguagem, Framework, Certificação, Conceito, Curso, Livro) e status (Não Iniciado, Em Progresso, Concluído, Pausado)
- **Tópicos**: adicionar tópicos com peso e estimativa de horas. Marcar como concluído
- **Roadmap visual**: barra de progresso calculada pelo peso dos tópicos concluídos
- **Sessões de estudo**: registrar tempo de estudo com notas e nível de confiança (1-5)
- **Estatísticas**: horas totais, sessões por semana, planos ativos

### Board Kanban (Alt+4)

Board de tarefas por projeto:

- **Colunas**: customizáveis por projeto (ex: Backlog, A Fazer, Fazendo, Revisão, Concluído)
- **Drag-and-drop**: arrastar cards entre colunas
- **Quick-move**: botão para avançar tarefa para próxima coluna sem arrastar
- **Filtros**: por tipo (Feature, Bug, Tech Debt, Improvement, Chore), prioridade (Low, Medium, High, Urgent), responsável e label
- **WIP limits**: limite de tarefas por coluna
- **Cards**: mostram tipo, prioridade, labels, due date, assignee, indicador de bloqueio e checklist progress
- **Task detail**: dialog completo com título, descrição, tipo, prioridade, assignee, due date, labels, checklist (Definition of Done), dependências, comentários com markdown

### Projetos (Alt+5)

- Criar projetos com nome, chave única (ex: DEMO, PROJ) e descrição
- Cada projeto gera automaticamente colunas padrão no board
- Visão de lista com link para o board

### Labels (Alt+6)

- Criar labels com nome e cor (paleta de 12 cores)
- Aplicar labels em tarefas para categorizar e filtrar
- Labels compartilhadas entre projetos do mesmo workspace

### Métricas (Alt+7)

Dashboard analítico:

- **Cards**: total de tarefas, concluídas (7 e 30 dias), lead time médio, cycle time
- **Throughput semanal**: gráfico de barras das últimas 8 semanas
- **Por tipo**: breakdown Feature/Bug/Tech Debt/Improvement/Chore com percentual
- **Por prioridade**: breakdown Low/Medium/High/Urgent com percentual
- **Por projeto**: progresso de cada projeto com barra

### Skills (Alt+8)

Biblioteca de skills para agentes de IA:

- **11 skills** com prefixo `maestro-` organizadas por categoria (Setup, Agente, Fluxo de Trabalho, Planejamento, Qualidade, Registro)
- **Instalar**: um clique instala o arquivo SKILL.md em `.claude/skills/` do projeto alvo
- **Instalar todas**: botão para instalar todas as skills de uma vez
- **Preview**: ver o conteúdo da skill antes de instalar
- **Diretório destino**: selecionar o projeto onde instalar as skills

### Instruções (Alt+9)

Guia de uso com explicações de cada tela e fluxo de trabalho.

## Recursos gerais

| Recurso | Descrição |
|---|---|
| **Tema dark/light** | Toggle na sidebar, aplica em todas as telas |
| **Pomodoro** | Timer de 25 min na sidebar com play/pause e reset |
| **Busca global** | `Ctrl+K` abre busca por título ou código de tarefa |
| **Workspaces** | Isolamento completo com banco separado, emoji, cor e descrição customizáveis |
| **Obsidian sync** | Auto-sync a cada 5 min, vault configurável por workspace/projeto |
| **Backup** | Exportar banco SQLite a qualquer momento |
| **Atalhos** | `Alt+1` a `Alt+9` para navegar entre telas, `Ctrl+K` para busca |

## API REST

A API roda em `http://127.0.0.1:9777/api` sem autenticação. Todos os endpoints retornam JSON.

### Endpoints

| Recurso | Método | Endpoint | Descrição |
|---|---|---|---|
| Health | GET | `/api/health` | Status da API |
| Projetos | POST | `/api/projects` | Criar projeto |
| Projetos | GET | `/api/projects` | Listar projetos |
| Projetos | GET | `/api/projects/metrics` | Métricas por projeto |
| Projetos | GET | `/api/projects/{id}/board` | Board completo do projeto |
| Tarefas | POST | `/api/tasks` | Criar tarefa |
| Tarefas | GET | `/api/tasks` | Listar tarefas (filtros: project_id, column_id, type, priority) |
| Tarefas | GET | `/api/tasks/{code}` | Detalhe da tarefa por código (ex: DEMO-1) |
| Tarefas | PATCH | `/api/tasks/{code}` | Atualizar tarefa |
| Tarefas | DELETE | `/api/tasks/{code}` | Soft-delete da tarefa |
| Tarefas | POST | `/api/tasks/{code}/move` | Mover para coluna (body: {column_id}) |
| Checklist | POST | `/api/tasks/{code}/checklist` | Adicionar item de checklist |
| Checklist | PATCH | `/api/tasks/checklist/{id}/toggle` | Toggle checked |
| Checklist | DELETE | `/api/tasks/checklist/{id}` | Remover item |
| Dependências | POST | `/api/tasks/{code}/dependencies` | Adicionar dependência |
| Dependências | DELETE | `/api/tasks/{code}/dependencies/{id}` | Remover dependência |
| Context | GET | `/api/tasks/{code}/context` | Contexto completo da tarefa |
| Context | GET | `/api/tasks/{code}/flow` | Fluxo de trabalho da tarefa |
| Labels | POST | `/api/labels` | Criar label |
| Labels | GET | `/api/labels` | Listar labels |
| Labels | DELETE | `/api/labels/{id}` | Remover label |
| Labels | POST | `/api/labels/{id}/tasks/{task_id}` | Aplicar label em tarefa |
| Labels | DELETE | `/api/labels/{id}/tasks/{task_id}` | Remover label de tarefa |
| Comentários | POST | `/api/comments` | Criar comentário |
| Comentários | GET | `/api/comments` | Listar comentários (filtro: task_id) |
| Comentários | PATCH | `/api/comments/{id}` | Editar comentário |
| Comentários | DELETE | `/api/comments/{id}` | Remover comentário |
| Documentos | POST | `/api/documents` | Criar documento |
| Documentos | GET | `/api/documents` | Listar documentos |
| Documentos | PUT | `/api/documents/{id}` | Atualizar documento |
| Documentos | DELETE | `/api/documents/{id}` | Remover documento |
| Atividade | GET | `/api/activity` | Log de atividades |
| Diario | GET | `/api/daily/{date}` | Nota do dia (YYYY-MM-DD) |
| Diario | POST | `/api/daily/{date}` | Criar/atualizar nota do dia |
| Diario | PATCH | `/api/daily/{date}/report` | Append ao relatório do dia |
| Estudos | POST | `/api/study/plans` | Criar plano de estudo |
| Estudos | GET | `/api/study/plans` | Listar planos |
| Estudos | GET | `/api/study/plans/{id}` | Detalhe do plano |
| Estudos | PATCH | `/api/study/plans/{id}` | Atualizar plano |
| Estudos | DELETE | `/api/study/plans/{id}` | Remover plano |
| Tópicos | POST | `/api/study/plans/{id}/topics` | Adicionar tópico |
| Tópicos | GET | `/api/study/plans/{id}/topics` | Listar tópicos |
| Tópicos | PATCH | `/api/study/topics/{id}` | Atualizar tópico |
| Tópicos | DELETE | `/api/study/topics/{id}` | Remover tópico |
| Sessões | POST | `/api/study/sessions` | Registrar sessão de estudo |
| Sessões | GET | `/api/study/sessions` | Listar sessões (filtro: date) |
| Stats | GET | `/api/study/stats` | Estatísticas de estudo |

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
| `maestro-run` | Setup | Iniciar a aplicação (GUI + API) |
| `maestro-api-agent` | Agente | Ensina o agente a interagir com a API REST |
| `maestro-task-workflow` | Fluxo | Fluxo completo: pegar task, implementar, mover, documentar |
| `maestro-project-setup` | Setup | Criar projeto com colunas e labels padrão |
| `maestro-sprint-planning` | Planejamento | Planejar sprint com estimativas e priorização |
| `maestro-code-review-log` | Qualidade | Registrar code reviews como comentários |
| `maestro-bug-triage` | Qualidade | Triagem de bugs com prioridade e reprodução |
| `maestro-daily-standup` | Registro | Gerar relatório de standup automático |
| `maestro-tech-debt-tracker` | Qualidade | Registrar e priorizar dívida técnica |
| `maestro-documentation-writer` | Registro | Gerar documentação a partir do código |
| `maestro-daily-report` | Registro | Relatório diário com notas, atividade e resumo em bullet list |

## Tipos de tarefa

| Tipo | Uso |
|---|---|
| `FEATURE` | Nova funcionalidade |
| `BUG` | Correção de bug |
| `TECH_DEBT` | Dívida técnica |
| `IMPROVEMENT` | Melhoria em funcionalidade existente |
| `CHORE` | Tarefa operacional |

## Prioridades

| Prioridade | Nível |
|---|---|
| `LOW` | Baixa |
| `MEDIUM` | Média |
| `HIGH` | Alta |
| `URGENT` | Urgente |

## Banco de dados

SQLite local com isolamento por workspace:

```
~/.maestro-local/
├── config.json                     # Workspaces, vaults, tema
└── workspaces/
    ├── default/maestro.db          # Workspace padrão
    └── {workspace-id}/maestro.db   # Workspaces adicionais
```

O banco é criado automaticamente na primeira execução. Cada workspace tem seu próprio arquivo, garantindo isolamento total dos dados.

## Estrutura do código

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
│   ├── workspace_selector.py # Seletor de workspace com emoji/cor/descrição
│   └── views/
│       ├── daily_view.py        # Meu Dia + Obsidian sync + relatório
│       ├── dashboard_view.py    # Dashboard com resumo e atividade
│       ├── study_view.py        # Planos de estudo + tópicos + sessões
│       ├── board_view.py        # Kanban board + TaskCard + filtros
│       ├── task_detail_dialog.py # Dialog completo de tarefa
│       ├── projects_view.py     # Lista/criação de projetos
│       ├── labels_view.py       # CRUD de labels com paleta
│       ├── metrics_view.py      # Dashboard de métricas
│       ├── skills_view.py       # Skills para agentes de IA
│       └── guide_view.py        # Instruções de uso
└── skills/
    └── catalog.py           # Catálogo de 11 skills com conteúdo SKILL.md
```

## Requisitos

- Python 3.10+
- Qt 6 (instalado automaticamente com PySide6)
- Linux, macOS ou Windows
