# Maestro Local

Cliente desktop local do Agentic Dev Maestro. Organização de tarefas e facilitação do ciclo de desenvolvimento, com API embutida para integração com agentes de IA.

## Requisitos

- Python 3.10+
- Qt 6 (instalado automaticamente com PySide6)

## Instalação

```bash
cd local-client
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Executar

```bash
# Via módulo Python
python -m maestro_local

# Via entry point (após pip install -e .)
maestro

# Com porta customizada
python -m maestro_local --port 8888
```

A aplicação inicia:
- **GUI desktop** (PySide6/Qt) — interface gráfica com kanban board, projetos, labels e métricas
- **API REST** em `http://127.0.0.1:9777` — para integração com agentes de IA

## Funcionalidades

### Interface Gráfica
- **Board Kanban** — colunas configuráveis, cards com tipo/prioridade/labels/checklist
- **Projetos** — criar e gerenciar projetos com chave única (ex: DEMO)
- **Task Detail** — edição completa: descrição, objetivo, aceite, estimativa, tipo, prioridade, labels, checklist, dependências, comentários, atividade
- **Labels** — criar labels com cores, aplicar em tarefas
- **Métricas** — total de tarefas, concluídas 7/30d, lead time, breakdown por tipo e projeto

### API REST (para agentes)
A API roda em `http://127.0.0.1:9777/api` sem autenticação.

| Recurso | Endpoints |
|---|---|
| Health | `GET /api/health` |
| Projetos | `POST/GET /api/projects`, `GET /api/projects/metrics`, `GET /api/projects/{id}/board` |
| Tarefas | `POST/GET /api/tasks`, `GET/PATCH/DELETE /api/tasks/{code}`, `POST /api/tasks/{code}/move` |
| Checklist | `POST /api/tasks/{code}/checklist`, `PATCH /api/tasks/checklist/{id}/toggle`, `DELETE /api/tasks/checklist/{id}` |
| Dependencias | `POST /api/tasks/{code}/dependencies`, `DELETE /api/tasks/{code}/dependencies/{id}` |
| Context | `GET /api/tasks/{code}/context`, `GET /api/tasks/{code}/flow` |
| Labels | `POST/GET /api/labels`, `DELETE /api/labels/{id}`, `POST/DELETE /api/labels/{id}/tasks/{task_id}` |
| Comentarios | `GET/POST /api/comments`, `PATCH/DELETE /api/comments/{id}` |
| Documentos | `GET/POST /api/documents`, `PUT/DELETE /api/documents/{id}` |
| Atividade | `GET /api/activity` |

### Banco de dados
SQLite local (`maestro.db`), criado automaticamente na primeira execução. Sem necessidade de configuração.

## Estrutura

```
local-client/
  maestro_local/
    __main__.py          # Entry point
    db/models.py         # SQLAlchemy models (SQLite)
    api/
      app.py             # FastAPI endpoints
      server.py          # Thread runner (uvicorn)
    gui/
      theme.py           # Dark theme stylesheet
      main_window.py     # Main window + sidebar navigation
      views/
        board_view.py    # Kanban board
        task_detail_dialog.py  # Task detail dialog
        projects_view.py # Projects list/create
        labels_view.py   # Labels CRUD
        metrics_view.py  # Metrics dashboard
```

## Tipos de tarefa

- `FEATURE` — nova funcionalidade
- `BUG` — correção de bug
- `TECH_DEBT` — dívida técnica
- `IMPROVEMENT` — melhoria
- `CHORE` — tarefa operacional

## Prioridades

`LOW` | `MEDIUM` | `HIGH` | `URGENT`
