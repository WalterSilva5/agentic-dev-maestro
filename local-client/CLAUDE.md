# Maestro Local — CLAUDE.md

## Visão geral

Cliente desktop local do Agentic Dev Maestro. Organiza tarefas e facilita o ciclo de desenvolvimento com GUI (PySide6/Qt) e API REST embutida (FastAPI) para agentes de IA.

## Stack

- **Python 3.10+**
- **PySide6** (Qt 6) — interface gráfica desktop
- **FastAPI + uvicorn** — API REST embutida (thread daemon, porta 9777)
- **SQLAlchemy 2.0 + SQLite** — banco de dados local por workspace
- **Pydantic** — validação de request bodies

## Estrutura

```
local-client/
  maestro_local/
    __main__.py              # Entry point (init_db -> start_api -> QApplication)
    config.py                # Config JSON (~/.maestro-local/config.json)
    db/models.py             # SQLAlchemy models + get_session/switch_db
    api/
      app.py                 # FastAPI com todos os endpoints
      server.py              # start_api() — roda uvicorn em thread daemon
    gui/
      theme.py               # ThemeColors dataclass + LIGHT/DARK + build_stylesheet
      main_window.py         # MainWindow com sidebar + QStackedWidget
      workspace_selector.py  # Seletor de workspace (Obsidian-style)
      views/
        dashboard_view.py    # Dashboard com resumo, vencidas, atividade, projetos
        board_view.py        # Kanban board + TaskCard + ColumnWidget + FilterBar
        task_detail_dialog.py # Dialog completo de tarefa (tabs: info, checklist, deps, comments, activity)
        projects_view.py     # Lista/criação de projetos
        labels_view.py       # CRUD de labels com paleta de cores
        metrics_view.py      # Dashboard de métricas
        study_view.py        # Planos de estudo + tópicos + sessões
        daily_view.py        # Diário de trabalho + Obsidian sync
        skills_view.py       # Skills para agentes de IA
        guide_view.py        # Instruções de uso
    skills/
      catalog.py             # Catálogo de 11 skills com prefixo maestro-
```

## Executar

```bash
cd local-client
source .venv/bin/activate
python -m maestro_local          # porta padrão 9777
python -m maestro_local -p 8888  # porta customizada
```

## Arquitetura GUI

A GUI usa **property-based CSS selectors** para estilização consistente com troca de tema:
- `setProperty("class", "card")` + `QFrame[class="card"]` no stylesheet global
- Classes disponíveis: `card`, `cardTitle`, `hint`, `sectionLabel`, `secondary`, `mono`, `preview`, `quickMove`
- Tema é aplicado via `build_stylesheet(ThemeColors)` no `MainWindow._apply_theme()`
- Trocar tema chama `set_theme()` + `_apply_theme()` — todos os widgets atualizam automaticamente

Navegação por sidebar com 9 itens (Dashboard, Diário, Estudos, Board, Projetos, Labels, Métricas, Skills, Instruções). Atalhos `Alt+1` a `Alt+9`.

### Workspaces
- Cada workspace tem banco SQLite isolado em `~/.maestro-local/workspaces/{id}/maestro.db`
- `switch_db(path)` troca a engine global do SQLAlchemy
- Config persistida em `~/.maestro-local/config.json`

### Dashboard
- Cards de resumo: tarefas ativas, concluídas 7d, vencidas, em progresso
- Lista de tarefas vencidas clicáveis
- Atividade recente agrupada por data
- Projetos com progress bar e contagem por coluna
- Sinais: `task_clicked(int)`, `project_clicked(int)`

### Board
- TaskCard com drag-and-drop + botão "Mover →" (quick move para próxima coluna)
- FilterBar com busca, tipo, prioridade e filtro por responsável
- ColumnWidget com WIP limit, contagem, quick-add input
- Code review obrigatório para coluna "Revisão"
- Auto-refresh a cada 5s (hash-based)

### Diário
- Notas markdown com template e preview
- Geração de relatório automático
- Sincronização com Obsidian Vault (manual + auto-sync a cada 5 min)
- Backup do banco de dados

## API

Base URL: `http://127.0.0.1:9777/api`

Sem autenticação. Tarefas identificadas por código (`KEY-NUM`, ex: `DEMO-1`) ou ID numérico.

### Projetos e Tarefas
- `GET /api/health`
- `POST/GET /api/projects` — CRUD de projetos
- `GET /api/projects/{id}/board` — board com colunas e tarefas
- `GET /api/projects/metrics` — métricas agregadas
- `POST/GET /api/tasks` — CRUD de tarefas
- `GET/PATCH/DELETE /api/tasks/{code}` — por código
- `POST /api/tasks/{code}/move` — mover entre colunas
- `POST /api/tasks/{code}/checklist` — checklist
- `POST /api/tasks/{code}/dependencies` — dependências
- `GET /api/tasks/{code}/context` — contexto agregado
- `GET /api/tasks/{code}/flow` — fluxo da tarefa

### Diário
- `GET/POST /api/daily/{date}` — notas do dia
- `PATCH /api/daily/{date}/report` — append ao relatório (não sobrescreve)

### Estudos
- `POST/GET /api/study/plans` — planos de estudo
- `GET/PATCH/DELETE /api/study/plans/{id}` — CRUD plano
- `GET/POST /api/study/plans/{id}/topics` — tópicos
- `PATCH/DELETE /api/study/topics/{id}` — CRUD tópico
- `PATCH /api/study/plans/{id}/topics/reorder` — reordenar
- `POST /api/study/sessions` — sessões de estudo
- `GET /api/study/sessions?date=YYYY-MM-DD` — sessões por data
- `GET /api/study/stats` — estatísticas gerais

### Outros
- `POST/GET /api/labels` — labels
- `GET/POST /api/comments` — comentários
- `PATCH/DELETE /api/comments/{id}` — editar/deletar comentário
- `POST/GET /api/documents` — documentos
- `PUT/DELETE /api/documents/{id}` — editar/deletar documento
- `GET /api/activity` — log de atividade

## Convenções

- App local, single-user, sem autenticação
- Workspaces com bancos SQLite isolados
- Task codes no formato `KEY-NUMBER` (ex: `DEMO-1`)
- Colunas padrão criadas com projeto: Backlog, A fazer, Fazendo, Revisão, Concluído
- Tipos: `FEATURE`, `BUG`, `TECH_DEBT`, `IMPROVEMENT`, `CHORE`
- Prioridades: `LOW`, `MEDIUM`, `HIGH`, `URGENT`
- Comentários: `COMMENT`, `CODE_REVIEW`, `COMMIT_REF`, `DEPLOY_LOG`
- Activity log registra ações em tasks (create, update, move, delete, comment)

## Skills para agentes

11 skills com prefixo `maestro-` no catálogo (`skills/catalog.py`):
- `maestro-run` — iniciar a aplicação
- `maestro-api-agent` — interagir com a API REST
- `maestro-task-workflow` — fluxo completo de trabalho
- `maestro-project-setup` — criar projeto com colunas e labels
- `maestro-sprint-planning` — planejar sprint
- `maestro-code-review-log` — registrar code reviews
- `maestro-bug-triage` — triagem de bugs
- `maestro-daily-standup` — standup automático
- `maestro-tech-debt-tracker` — dívida técnica
- `maestro-documentation-writer` — gerar documentação
- `maestro-daily-report` — relatório diário (com PATCH append)

## Módulo de Estudos

- **Planos**: título, categoria (LINGUAGEM/FRAMEWORK/CERTIFICACAO/CONCEITO/CURSO/LIVRO), status (PLANEJADO/EM_ANDAMENTO/PAUSADO/CONCLUIDO/ABANDONADO)
- **Tópicos**: título, peso, estimativa de horas, horas registradas, notas, status (PENDENTE/ESTUDANDO/REVISAO/CONCLUIDO/PULADO)
- **Sessões**: registro de tempo com notas e nível de confiança (1-5)
- **Progresso**: calculado automaticamente (peso dos concluídos / peso total x 100)
