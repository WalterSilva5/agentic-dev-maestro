# Maestro Local — CLAUDE.md

## Visão geral

Cliente desktop local do Agentic Dev Maestro. Organiza tarefas e facilita o ciclo de desenvolvimento com GUI (PySide6/Qt) e API REST embutida (FastAPI) para agentes de IA.

## Stack

- **Python 3.10+**
- **PySide6** (Qt 6) — interface gráfica desktop
- **FastAPI + uvicorn** — API REST embutida (thread daemon)
- **SQLAlchemy 2.0 + SQLite** — banco de dados local (`maestro.db`)
- **Pydantic** — validação de request bodies

## Estrutura

```
local-client/
  maestro_local/
    __main__.py          # Entry point (init_db → start_api → QApplication)
    db/models.py         # SQLAlchemy models + get_session/init_db
    api/
      app.py             # FastAPI com todos os endpoints
      server.py          # start_api() — roda uvicorn em thread daemon
    gui/
      theme.py           # DARK_STYLE + constantes de cores
      main_window.py     # MainWindow com sidebar + QStackedWidget
      views/
        board_view.py    # Kanban board + TaskCard + ColumnWidget
        task_detail_dialog.py  # Dialog completo de tarefa
        projects_view.py # Lista/criação de projetos
        labels_view.py   # CRUD de labels com paleta de cores
        metrics_view.py  # Dashboard de métricas
```

## Executar

```bash
cd local-client
source .venv/bin/activate
python -m maestro_local          # porta padrão 9777
python -m maestro_local -p 8888  # porta customizada
```

## API

Base URL: `http://127.0.0.1:9777/api`

Sem autenticação. Tarefas são identificadas por código (`KEY-NUM`, ex: `DEMO-1`) ou ID numérico.

Endpoints principais:
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
- `POST/GET /api/labels` — labels
- `POST/GET /api/comments` — comentários
- `POST/GET /api/documents` — documentos
- `GET /api/activity` — log de atividade

## Banco de dados

SQLite local. O arquivo `maestro.db` é criado automaticamente na primeira execução. Modelos em `db/models.py`.

## Convenções

- Sem autenticação — app local, single-user
- Sem multi-tenant — sem empresas/workspaces
- Task codes no formato `KEY-NUMBER` (ex: `DEMO-1`)
- Colunas padrão criadas com projeto: Backlog, A fazer, Fazendo, Revisão, Concluído
- Tipos: FEATURE, BUG, TECH_DEBT, IMPROVEMENT, CHORE
- Prioridades: LOW, MEDIUM, HIGH, URGENT
- Comentários: COMMENT, CODE_REVIEW, COMMIT_REF, DEPLOY_LOG
- Activity log registra ações em tasks (create, update, move, delete, comment)
