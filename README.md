> 🇧🇷 [Versão em português](README.ptbr.md)

# Agentic Dev Maestro

Desktop application for project management, work journaling, and study tracking, with an embedded REST API for integration with AI agents.

![Dashboard Light](local-client/docs/screenshots/dashboard-light.png)

## What it is

Maestro is a local tool for developers who want to organize their daily work, manage tasks on a kanban board, track their studies, and integrate AI agents into their development workflow. Everything runs locally — no external server, no account, no internet dependency.

### Key differentiators

- **Fully local**: data in SQLite, native desktop GUI, no cloud
- **Assistant**: internal AI agent (LangGraph) with a configurable provider (LM Studio, opencode) that acts on the board
- **Cronista**: records meetings/study sessions, transcribes locally with Whisper, and summarizes with AI (the former wsi-cronista project, now integrated)
- **Agent API**: AI agents create tasks, move them on the board, log code reviews, and generate reports — all via REST
- **Ready-made skills**: 12 installable skills that teach agents how to use Maestro
- **Isolated workspaces**: each workspace has its own database, letting you separate personal from professional projects
- **Obsidian sync**: synchronizes daily notes and tasks with your Obsidian vault
- **Integrated Pomodoro**: timer on the Dashboard for focus sessions

## Installation with an AI agent

Ask your AI agent (Claude Code, Cursor, etc.) to install Maestro automatically. Just send something like:

> Clone the repository https://github.com/WalterSilva5/agentic-dev-maestro.git, run install.sh in the local-client directory, create a desktop shortcut for run.sh, and explain to me how to use the application.

The agent will:

1. Clone the repository
2. Run `local-client/install.sh` (creates a venv + installs dependencies)
3. Create a `.desktop` shortcut on the desktop pointing to `local-client/run.sh`
4. Explain the main features: kanban board, my day, skills, agent API

After installation, open Maestro from the shortcut or run `local-client/run.sh`. On the **Skills** tab, install the skills into your project's directory — they teach the agent how to use the Maestro API to create tasks, document progress, and generate reports.

## Features

### My Day (home)
Main screen with daily notes in markdown, a pre-configured template, automatic report generation with an activity summary, and synchronization with an Obsidian vault. Date picker with a popup calendar for navigating between days. Includes a prompt hint so AI agents can generate the summary via a skill.

### Dashboard
Central hub organized into tabs: **Overview** (Pomodoro, summary cards, overdue tasks, recent activity, and progress by project), **Metrics**, **TODOs**, and **Labels**.

### Kanban Board
Board with drag-and-drop, columns customizable per project, filters by type/priority/assignee, a quick-move button to advance tasks, WIP limits, and a mandatory code review indicator. Agents always create review tasks (`requiresHuman: true`) so the developer can validate changes.

### Assistant
Internal AI assistant that runs with your own provider (local LM Studio, opencode, or any OpenAI-compatible API). It reads the board, suggests priorities, requests task reviews, creates TODOs, and comments on tasks — all within the application. Built with LangGraph and internal tools. Configurable under Settings → AI Providers.

### Transcriptions
Records meetings and study sessions (microphone and/or system audio via PipeWire/PulseAudio), transcribes locally with faster-whisper, and generates structured summaries with AI: meetings become key points/decisions/action items; study sessions become concepts/exercises/related topics. Searchable history, global Ctrl+Shift+R shortcut, and a button to save the summary to My Day. Features migrated from the wsi-cronista project.

### Projects
Create and manage projects with a unique key (e.g., DEMO). Each project has its own board columns, tasks, labels, and metrics.

### Labels
Create labels with colors from the palette and apply them to tasks to categorize and filter. Labels are shared across projects in the same workspace.

### Metrics
Dashboard with total tasks, completed (7 and 30 days), average lead time, cycle time, weekly throughput with a bar chart, and a breakdown by type, priority, and project.

### Studies
Study plans with a visual roadmap, categories (Language, Framework, Certification, Concept, Course, Book), weighted topics, and sessions with hour tracking and a confidence level (1-5).

### Skills
Library of 12 skills for AI agents. Each skill is a SKILL.md file that can be installed into the project's `.claude/skills/` directory. "Install all" button for quick setup.

### Instructions
Application usage guide with 12 sections, including explanations of each screen, the workflow, the role of agents, and review tasks.

### Settings
General settings screen with:
- **AI Providers**: register/select OpenAI-compatible providers (LM Studio, Ollama, OpenAI, OpenRouter, Groq, DeepSeek, Mistral, Gemini, Together, opencode), with a connection test. Used by the Assistant
- **Pomodoro**: configurable session duration (1-120 min)
- **Push notifications**: periodic desktop notifications with a custom message, configurable interval, and enable/disable toggle

### General features
- Dark/light theme with a toggle in the sidebar
- Configurable Pomodoro timer on the Dashboard
- Quick access to Transcriptions in the sidebar (record in 1 click)
- Periodic push notifications with a custom message
- Global task search (Ctrl+K)
- Isolated workspaces with separate databases, customizable emojis and colors
- Database backup
- Auto-sync with an Obsidian vault per workspace (every 5 min)
- Vault configurable per workspace and project

## Quick Start (manual)

```bash
cd local-client
./install.sh    # creates venv + installs dependencies + validates
./run.sh        # runs the application
```

Or:

```bash
cd local-client
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m maestro_local
```

The application opens with:
- **Desktop GUI** — complete interface with 10 screens in the menu (Metrics, TODOs, and Labels became Dashboard tabs)
- **REST API** — `http://127.0.0.1:9777/api` for AI agents

### Custom port

```bash
./run.sh --port 8888
```

## REST API for agents

The API runs at `http://127.0.0.1:9777/api` without authentication. Main endpoints:

| Resource | Endpoints |
|---|---|
| Health | `GET /api/health` |
| Projects | `POST/GET /api/projects`, `GET /api/projects/metrics` |
| Tasks | `POST/GET /api/tasks`, `GET/PATCH/DELETE /api/tasks/{code}`, `POST /api/tasks/{code}/move` |
| Checklist | `POST /api/tasks/{code}/checklist`, `PATCH/DELETE /api/tasks/checklist/{id}` |
| Labels | `POST/GET /api/labels`, `POST/DELETE /api/labels/{id}/tasks/{task_id}` |
| Comments | `GET/POST /api/comments`, `PATCH/DELETE /api/comments/{id}` |
| Journal | `GET/POST /api/daily/{date}`, `PATCH /api/daily/{date}/report` |
| TODOs | `GET/POST /api/todos`, `PATCH/DELETE /api/todos/{id}` |
| Studies | `POST/GET /api/study/plans`, `PATCH/DELETE /api/study/plans/{id}` |
| History | `GET /api/tasks/{code}/history` |
| Changelog | `GET /api/projects/{project_id}/changelog?days=7` |
| Activity | `GET /api/activity` |

## Skills for AI agents

| Skill | What it does |
|---|---|
| `maestro-run` | Start the application (GUI + API) |
| `maestro-api-agent` | Teaches the agent to use the REST API |
| `maestro-task-workflow` | Complete workflow: pick a task, implement, move, document |
| `maestro-project-setup` | Create a project with default columns and labels |
| `maestro-sprint-planning` | Plan a sprint with estimates and prioritization |
| `maestro-code-review-log` | Log code reviews as comments |
| `maestro-bug-triage` | Bug triage with priority and reproduction |
| `maestro-daily-standup` | Generate an automatic standup report |
| `maestro-tech-debt-tracker` | Log and prioritize technical debt |
| `maestro-documentation-writer` | Generate documentation from code |
| `maestro-daily-report` | Daily report with notes, activity, and summary (supports partial mode) |
| `maestro-context-loader` | Load the full workspace context to resume work from where you left off |

## Screenshots

![Dashboard](local-client/docs/screenshots/dashboard-light.png)
![My Day](local-client/docs/screenshots/meudia-light.png)
![Board with sprints](local-client/docs/screenshots/board-light.png)
![Sprint Planning](local-client/docs/screenshots/planejamento-light.png)
![Studies with the assistant](local-client/docs/screenshots/estudos-light.png)
![Assistant](local-client/docs/screenshots/chat-light.png)
![Meetings (live copilot)](local-client/docs/screenshots/reunioes-light.png)
![Projects](local-client/docs/screenshots/projetos-light.png)
![Skills](local-client/docs/screenshots/skills-light.png)
![Instructions](local-client/docs/screenshots/instrucoes-light.png)
![Settings](local-client/docs/screenshots/configuracoes-light.png)

## Project structure

```
agentic-dev-maestro/
├── local-client/              # Main app (Python/PySide6)
│   ├── maestro_local/         # Source code
│   │   ├── gui/views/         # interface screens (Dashboard with tabs)
│   │   ├── api/               # FastAPI endpoints
│   │   ├── db/                # SQLAlchemy models + SQLite
│   │   └── skills/            # Catalog of 12 skills
│   ├── install.sh             # Installation script
│   ├── run.sh                 # Run script
│   ├── pyproject.toml         # Python dependencies
│   └── docs/screenshots/      # Screenshots
│
├── web-client/                # Web client (NestJS + Angular) — in development
├── mcp/                       # MCP server for integration
├── docs/                      # Architecture documentation
├── CLAUDE.md                  # Guide for AI agents
└── README.md
```

## Data

Data lives in `~/.maestro-local/`:

```
~/.maestro-local/
├── config.json                # Settings (workspaces, vault paths, theme)
└── workspaces/
    ├── default/
    │   └── maestro.db         # SQLite database for the default workspace
    └── {workspace-id}/
        └── maestro.db         # SQLite database for each workspace
```

## Requirements

- Python 3.10+
- Operating system: Linux, macOS, or Windows
- Qt 6 (installed automatically with PySide6)

## License

Private License. Copyright (c) 2026 WalterSilva5. All rights reserved. See the [LICENSE](LICENSE) file for details.
