> 🇧🇷 [Versão em português](README.ptbr.md)

# Maestro Local

Desktop client for Agentic Dev Maestro. Organizes tasks, work journal, and studies, with an embedded REST API for integration with AI agents.

## Installation and running

### Quick (recommended)

```bash
./install.sh    # creates venv, installs deps, validates
./run.sh        # runs
```

### Manual

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m maestro_local
```

### Options

```bash
./run.sh --port 8888    # custom port (default: 9777)
```

### Global entry point

After `pip install -e .`, the `maestro` command becomes available in the venv PATH:

```bash
maestro              # default port
maestro --port 8888  # custom port
```

## What the application does

On startup, Maestro opens:
1. **Desktop GUI** (PySide6/Qt 6) — graphical interface with a lean menu (9 items) + a Tools hub that groups the extra features (+ Metrics, TODOs, and Labels as Dashboard tabs)
2. **REST API** (FastAPI/uvicorn) — `http://127.0.0.1:9777/api` in a daemon thread

The initial screen is **My Day**, which works as the application's home.

## Screens

### My Day (Alt+2) — home

Main screen for the workday:

- **Obsidian Vault**: select a vault by project/workspace, sync notes and tasks with Obsidian. Automatic sync every 5 minutes
- **Notes of the day**: markdown editor with a pre-configured template, rendered preview, button to insert the default template (Focus of the Day, Tasks, Blockers, Technical Notes)
- **Generate Report**: generates an automatic report with a list of tasks worked on, activities of the day, and summary
- **Date picker**: popup calendar to navigate between days (replaced the date combo box)
- **AI Tip**: next to the generated report, a button with a suggested prompt to ask an AI agent to summarize the day using the `maestro-daily-report` skill
- **Activity of the day**: timeline with all the day's actions (tasks created, moved, commented)
- **Database Backup**: export a copy of the SQLite database

### TODOs (Dashboard tab)

Quick list of pending items, separate from the board:

- **Simple list**: no columns, no project, no status flow
- **Add/complete/remove**: text field with Enter, checkbox per item (struck through when completed), remove button
- **Organization**: pending items at the top, completed ones at the bottom, with a counter
- **Clear completed**: button to remove all checked items at once
- **API**: manageable via `/api/todos`, so agents can also create and close TODOs

### Dashboard (Alt+1)

Central hub of the workspace, organized into **tabs**:

- **Overview**: Pomodoro highlighted, summary cards (active, completed, overdue, in-progress tasks), clickable overdue tasks, recent activity, and progress by project
- **Metrics**, **TODOs**, and **Labels** (previously their own pages)

### Studies (in Tools)

Learning module:

- **Study plans**: create plans with a name, category (Language, Framework, Certification, Concept, Course, Book), and status (Not Started, In Progress, Completed, Paused)
- **Topics**: add topics with weight and estimated hours. Mark as completed
- **Visual roadmap**: progress bar calculated from the weight of completed topics
- **Study sessions**: log study time with notes and confidence level (1-5)
- **Statistics**: total hours, sessions per week, active plans
- **Study assistant (on demand)**: in the plan detail view, a panel with buttons that trigger the AI for the chosen topic — **Explain**, **Exercises**, **Quiz** (with answer key), review **Flashcards**, **Build roadmap** (an agent flow: the AI first asks a few questions so you can add context — level, goal, available time, focus — and only then generates a tailored topic list, which you add to the plan with 1 click, without duplicating), and **Ask a question** (free-form question). Nothing is automatic: you click the action you want. Uses the configured AI provider
- **Attachments as context during creation**: when creating a plan, you can **attach files** (ebooks/documents: `.txt`, `.md`, `.pdf`, `.docx`, `.epub`). The text is extracted locally and used as **context together with the fields** (title, category, description) for the AI to generate the plan's **topics** with estimated hours. Without attachments, the plan is created normally (empty)

### Kanban Board (Alt+3)

Task board by project:

- **Columns**: customizable per project (e.g.: Backlog, To Do, Doing, Review, Done)
- **Sprints (planning long projects)**: each project can have sprints (name, goal, status planned/active/completed, dates, and **capacity** in man-days). The board has a **sprint selector** (All / Backlog / a sprint) that filters the cards, and each card has a **dropdown to move the task** between backlog and sprints. Activate (only one active per project), complete (unfinished tasks return to the backlog), and delete. Progress statistics and committed effort vs. capacity (⚠ when it exceeds). Desktop and web
- **Sprint Planning tab**: alongside the flow board, an **allocation** tab where the columns are **Backlog + each sprint** — drag the backlog into the sprints (via the selector on the card), see capacity vs. committed per sprint, and create/activate/complete sprints. Ideal for planning long projects across several future sprints
- **Drag-and-drop**: drag cards between columns
- **Quick-move**: button to advance a task to the next column without dragging
- **Filters**: by type (Feature, Bug, Tech Debt, Improvement, Chore), priority (Low, Medium, High, Urgent), assignee, and label
- **WIP limits**: task limit per column
- **Archiving**: cards in completion columns have an **"Archive"** action — they disappear from the board and go to a **separate board (Archived)**, from which they can be **unarchived**. Cards that have been completed for **more than 3 days are archived automatically** when opening the board. Available on desktop and web
- **Cards**: show type, priority, labels, due date, assignee, blocking indicator, and checklist progress
- **Task detail**: full dialog with title, description, type, priority, assignee, due date, labels, checklist (Definition of Done), dependencies, comments with markdown
- **Review tasks**: agents always create tasks with `requiresHuman: true` for the developer to validate changes

### Assistant (Alt+4)

Internal AI assistant that runs with your own provider:

- **OpenAI-compatible providers**: local LM Studio, opencode, or any API in the `/v1/chat/completions` format
- **Internal tools** (LangGraph): reads the board, lists tasks, requests review (creates a requires-dev task), comments on tasks, creates TODOs, and summarizes recent activity
- **Asynchronous execution**: runs in a separate thread, without freezing the interface
- **Configuration**: active provider defined in Settings → AI Providers (Base URL, API Key, and Model)

### Meetings (in Tools)

Recording, transcription, and summarization of meetings and studies (migrated from the wsi-cronista project):

- **Audio capture (Linux)**: microphone and/or system audio via PipeWire/PulseAudio (`parec`); `.monitor` sources for loopback
- **Local transcription**: faster-whisper, configurable model (tiny → large-v3), runs offline in a QThread
- **Meeting assistant**: extracts title, key points, decisions, actions (with owner), and open questions
- **Live assistant (meeting copilot)**: with the "Live assistant" toggle on, it transcribes during recording (~10s windows, `base` model for low latency) and a side panel with **Plan · Tips · Actions · Decisions · Questions** tabs is filled incrementally by the AI. In addition to extracting actions/decisions/questions, the copilot **builds an action plan** and **gives proactive tips** as the meeting progresses, using the **context of the workspace and the selected project** (name, description, and open tasks). It includes **"Ask the meeting"** — ask something and the AI answers based on what was said + the project context. The definitive (more accurate) transcription is still generated from the full WAV when stopping
- **Study assistant**: generates a summary, key concepts, practical exercises, related topics, and resources
- **Reused AI**: the analysis uses the provider configured in AI Providers (LM Studio/opencode)
- **Meeting → board**: the "Create tasks from actions" button turns the action items (from the live view or the summary) into tasks (type CHORE, `requires_human`) in the chosen project
- **History**: recordings saved in the workspace database, with text search
- **Integration**: the "Save to My Day" button appends the summary to the day's report
- **Global shortcut**: `Ctrl+Shift+R` starts/stops the recording (best-effort; may not work on Wayland)
- **Quick access**: a widget in the sidebar starts the recording in 1 click and shows the elapsed time

### Passwords (in Tools) — KeePass vault

- **Global vault** (one for the whole app, **not per workspace**) stored outside the per-workspace databases at `~/.maestro-local/vault.kdbx` (path configurable)
- Reads and writes the **`.kdbx`** format (KeePass 2.x via `pykeepass`); interoperates with existing KeePass vaults
- **Unlocked by a master password** (and/or key file); the master password is **never persisted** — kept only in memory and discarded on lock
- **Entries**: title, username, password, URL, group, notes; search and organization by groups; add/edit/delete
- **Copy-to-clipboard with auto-clear** (25s) and **auto-lock on inactivity** (5 min)
- Desktop-only (the vault runs in the local Python process)

### Library (in Tools) — dev tools hub (tabs)

- **Snippets & Prompts**: reusable code snippets and AI prompts, with kind (SNIPPET/PROMPT), language, tags; search by text/tags/language; copy-to-clipboard with a use counter
- **Runbooks**: setup/deploy/command cards with a category and one-click copy of the command
- **Import from code**: scan a folder for `TODO/FIXME/HACK/XXX` comments and import selected ones as tasks (linked to `file:line`) in the chosen project
- **Bug triage**: paste a stack trace/report → AI classifies title/severity/probable cause/steps → becomes a BUG task
- **Code review**: point at a repo + base (branch/ref) → AI reviews the git diff (summary, issues by severity, suggestions), optionally posted as a `CODE_REVIEW` comment on a task
- **Git**: repository cockpit — branch, ahead/behind, staged/unstaged/untracked changes, recent commits and open PRs (via `gh`, read-only)
- Available on desktop and on the web UI (`/biblioteca`); API `/api/snippets`, `/api/runbooks`, `/api/code/scan-todos`, `/api/code/import-todos`, `/api/bugs/triage`, `/api/code/review`, `/api/git/status`

### API tester (in Tools) — mini-Postman

- **Build/run HTTP requests**: method, URL, headers (JSON or `Key: value` per line), body; runs via the stdlib (no extra deps)
- **Save requests** per workspace and reload them; **execution history** (status, duration, URL)
- Available on desktop and on the web UI (`/api-tester`); API `/api/http-requests` (+ `/run`, `/history`)

### Knowledge base (in Tools) — second brain

- **Notes/wiki** (reuses `Document` with type `KB`) with `[[title]]` **backlinks** shown per note
- **AI Q&A over your notes** (RAG-lite: keyword retrieval + answer citing the notes used)
- Available on desktop and on the web UI (`/base`); API `/api/kb/notes`, `/api/kb/ask`

### Tools (Alt+5) — hub of extra features

To keep the sidebar lean, the extra features live behind a single **Tools** menu item that opens a **grid of icon cards** (a launcher). Clicking a card opens the feature and keeps **Tools** highlighted in the sidebar. Cards: **Studies**, **Meetings**, **Passwords**, **Library**, **API tester**, **Knowledge base**, **Practice English**. On the web UI it is `/ferramentas` (cards: Studies, Metrics, Labels, Library, API tester, Knowledge base).

### Practice English (in Tools)

Simple-but-effective conversational English practice (ideas distilled from the standalone *wsi-talk* project, without the weight):

- **AI conversation partner by level** (Beginner / Intermediate / Advanced / Free) with an optional topic; the AI stays at your level and asks one follow-up question per turn
- **Gentle coaching per turn**: a corrected/more natural version of your message, a short tip in Portuguese, and 0-3 useful words with **Portuguese pronunciation respelling** (e.g. `outside` → *áutsáid*) and meaning
- **Sample answer hint** for each question
- **Voice input**: record with the mic → transcribed by the offline Whisper (English) → sent automatically. Typing also works. Desktop-only, in-process; no persistence (ephemeral session)

### Projects (Alt+6)

- Create projects with a name, unique key (e.g.: DEMO, PROJ), and description
- Each project automatically generates default board columns
- List view with a link to the board

### Labels (Dashboard tab)

- Create labels with a name and color (palette of 12 colors)
- Apply labels to tasks to categorize and filter
- Labels shared across projects of the same workspace

### Metrics (Dashboard tab)

Analytics dashboard:

- **Cards**: total tasks, completed (7 and 30 days), average lead time, cycle time
- **Weekly throughput**: bar chart of the last 8 weeks
- **By type**: Feature/Bug/Tech Debt/Improvement/Chore breakdown with percentage
- **By priority**: Low/Medium/High/Urgent breakdown with percentage
- **By project**: progress of each project with a bar

### Skills (Alt+7)

Library of skills for AI agents:

- **12 skills** prefixed with `maestro-` organized by category (Setup, Agent, Workflow, Planning, Quality, Logging)
- **Install**: one click installs the SKILL.md file into the target project's `.claude/skills/`
- **Install all**: button to install all skills at once
- **Preview**: view the skill's content before installing
- **Target directory**: select the project where the skills will be installed

### Instructions (Alt+8)

Restructured usage guide with 12 sections, including explanations of each screen, the workflow, the role of the agents, and review tasks.

### Settings (Alt+9)

General settings screen:

- **AI Providers**: register and select OpenAI-compatible providers (LM Studio, Ollama, OpenAI, OpenRouter, Groq, DeepSeek, Mistral, Gemini, Together, opencode) used by the Assistant and by Transcriptions. Base URL, API Key, and Model fields, with a button to test the connection and add new providers
- **Transcriptions**: Whisper model (tiny → large-v3) and language used in local transcription
- **Pomodoro**: configurable session duration (1-120 minutes), updates the sidebar timer in real time
- **Push notifications**: periodic desktop notifications with a custom message, configurable interval (1-480 min), and an enable toggle. Disabled by default. Uses `QSystemTrayIcon` with a fallback to `notify-send`

## General features

| Feature | Description |
|---|---|
| **Dark/light theme** | Toggle in the sidebar, applies to all screens |
| **Pomodoro** | Configurable timer in the Dashboard with play/pause and reset |
| **Push notifications** | Periodic desktop reminders with customizable message and interval |
| **Global search** | `Ctrl+K` opens search by task title or code |
| **Workspaces** | Complete isolation with a separate database, customizable emoji, color, and description |
| **Obsidian sync** | Auto-sync every 5 min, vault configurable per workspace/project |
| **Backup** | Export the SQLite database at any time |
| **Shortcuts** | `Alt+1` to `Alt+9` + `Alt+0` for the 10 menu screens, `Ctrl+K` search, `Ctrl+Shift+R` recording |

## Web UI (web frontend)

In addition to the desktop GUI, there is a **web** frontend (React + Vite) served by the API itself — it starts up along with it. With the app running, access **`http://127.0.0.1:9777/`** in the browser.

- **Code**: `webui/` (React + Vite + axios + react-router), consumes the same REST API
- **Build**: `install.sh` builds automatically (if `npm` is available); FastAPI serves `webui/dist/` at the root `/`, keeping `/api/*`
- **Development** (hot-reload): `cd webui && npm run dev` (port 3000, with `/api → 9777` proxy)
- **Screens**: Dashboard, My Day, Studies, Projects, Board + task detail (description, checklist, comments, type/priority, move), Assistant (chat), Metrics, TODOs, Labels, and Settings (language, AI providers, Whisper). Workspace selector in the sidebar and light/dark theme. **Transcriptions** and **Skills** remain exclusive to the desktop GUI (audio capture and installation into a local directory)
- **Run only the web** (without the desktop GUI): `./run-web.sh` (or `python -m maestro_local.webmain`) — starts API + web at `http://127.0.0.1:9777/`
- **Installable PWA**: the web is a Progressive Web App (manifest + service worker in `webui/public/`). In the browser, use "Install app" to open it in its own window; it works offline for the shell (the API still requires the local server)

```bash
cd webui
npm install
npm run build      # generates webui/dist served by the API
# or, in dev:
npm run dev        # http://localhost:3000 (proxy to the API at 9777)
```

## REST API

The API runs at `http://127.0.0.1:9777/api` without authentication. All endpoints return JSON.

### Endpoints

| Resource | Method | Endpoint | Description |
|---|---|---|---|
| Health | GET | `/api/health` | API status |
| Projects | POST | `/api/projects` | Create project |
| Projects | GET | `/api/projects` | List projects |
| Projects | GET | `/api/projects/metrics` | Metrics by project |
| Projects | GET | `/api/projects/{id}/board` | Complete project board |
| Tasks | POST | `/api/tasks` | Create task |
| Tasks | GET | `/api/tasks` | List tasks (filters: project_id, column_id, type, priority) |
| Tasks | GET | `/api/tasks/{code}` | Task detail by code (e.g.: DEMO-1) |
| Tasks | PATCH | `/api/tasks/{code}` | Update task |
| Tasks | DELETE | `/api/tasks/{code}` | Soft-delete the task |
| Tasks | POST | `/api/tasks/{code}/move` | Move to column (body: {column_id}) |
| Checklist | POST | `/api/tasks/{code}/checklist` | Add checklist item |
| Checklist | PATCH | `/api/tasks/checklist/{id}/toggle` | Toggle checked |
| Checklist | DELETE | `/api/tasks/checklist/{id}` | Remove item |
| Dependencies | POST | `/api/tasks/{code}/dependencies` | Add dependency |
| Dependencies | DELETE | `/api/tasks/{code}/dependencies/{id}` | Remove dependency |
| Context | GET | `/api/tasks/{code}/context` | Complete task context |
| Context | GET | `/api/tasks/{code}/flow` | Task workflow |
| History | GET | `/api/tasks/{code}/history` | Structured development timeline (transitions, comments, code reviews, checklist) |
| Changelog | GET | `/api/projects/{project_id}/changelog?days=7` | Aggregated project changelog (completed tasks, in progress, activity per day) |
| Labels | POST | `/api/labels` | Create label |
| Labels | GET | `/api/labels` | List labels |
| Labels | DELETE | `/api/labels/{id}` | Remove label |
| Labels | POST | `/api/labels/{id}/tasks/{task_id}` | Apply label to task |
| Labels | DELETE | `/api/labels/{id}/tasks/{task_id}` | Remove label from task |
| Comments | POST | `/api/comments` | Create comment |
| Comments | GET | `/api/comments` | List comments (filter: task_id) |
| Comments | PATCH | `/api/comments/{id}` | Edit comment |
| Comments | DELETE | `/api/comments/{id}` | Remove comment |
| Documents | POST | `/api/documents` | Create document |
| Documents | GET | `/api/documents` | List documents |
| Documents | PUT | `/api/documents/{id}` | Update document |
| Documents | DELETE | `/api/documents/{id}` | Remove document |
| Activity | GET | `/api/activity` | Activity log |
| Journal | GET | `/api/daily/{date}` | Note of the day (YYYY-MM-DD) |
| Journal | POST | `/api/daily/{date}` | Create/update note of the day |
| Journal | PATCH | `/api/daily/{date}/report` | Append to the day's report |
| TODOs | GET | `/api/todos` | List TODOs (filter: done) |
| TODOs | POST | `/api/todos` | Create TODO |
| TODOs | PATCH | `/api/todos/{id}` | Update text or mark as completed |
| TODOs | DELETE | `/api/todos/{id}` | Remove TODO |
| Studies | POST | `/api/study/plans` | Create study plan |
| Studies | GET | `/api/study/plans` | List plans |
| Studies | GET | `/api/study/plans/{id}` | Plan detail |
| Studies | PATCH | `/api/study/plans/{id}` | Update plan |
| Studies | DELETE | `/api/study/plans/{id}` | Remove plan |
| Topics | POST | `/api/study/plans/{id}/topics` | Add topic |
| Topics | GET | `/api/study/plans/{id}/topics` | List topics |
| Topics | PATCH | `/api/study/topics/{id}` | Update topic |
| Topics | DELETE | `/api/study/topics/{id}` | Remove topic |
| Sessions | POST | `/api/study/sessions` | Log study session |
| Sessions | GET | `/api/study/sessions` | List sessions (filter: date) |
| Stats | GET | `/api/study/stats` | Study statistics |

### Example: create a task via curl

```bash
# Create project
curl -X POST http://127.0.0.1:9777/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Meu Projeto", "key": "MP"}'

# Create task
curl -X POST http://127.0.0.1:9777/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Implementar login", "project_id": 1, "type": "FEATURE", "priority": "HIGH"}'

# Move task
curl -X POST http://127.0.0.1:9777/api/tasks/MP-1/move \
  -H "Content-Type: application/json" \
  -d '{"column_id": 2}'
```

## Skills for AI agents

| Skill | Category | What it does |
|---|---|---|
| `maestro-run` | Setup | Start the application (GUI + API) |
| `maestro-api-agent` | Agent | Teaches the agent to interact with the REST API |
| `maestro-task-workflow` | Workflow | Complete flow: pick a task, implement, move, document |
| `maestro-project-setup` | Setup | Create a project with default columns and labels |
| `maestro-sprint-planning` | Planning | Plan a sprint with estimates and prioritization |
| `maestro-code-review-log` | Quality | Log code reviews as comments |
| `maestro-bug-triage` | Quality | Bug triage with priority and reproduction |
| `maestro-daily-standup` | Logging | Generate an automatic standup report |
| `maestro-tech-debt-tracker` | Quality | Log and prioritize technical debt |
| `maestro-documentation-writer` | Logging | Generate documentation from the code |
| `maestro-daily-report` | Logging | Daily report with notes, activity, and a bullet-list summary (supports partial mode) |
| `maestro-context-loader` | Agent | Load the complete workspace context to resume work from where you left off |

## Task types

| Type | Use |
|---|---|
| `FEATURE` | New functionality |
| `BUG` | Bug fix |
| `TECH_DEBT` | Technical debt |
| `IMPROVEMENT` | Improvement to existing functionality |
| `CHORE` | Operational task |

## Priorities

| Priority | Level |
|---|---|
| `LOW` | Low |
| `MEDIUM` | Medium |
| `HIGH` | High |
| `URGENT` | Urgent |

## Database

Local SQLite with isolation per workspace:

```
~/.maestro-local/
├── config.json                     # Workspaces, vaults, theme
└── workspaces/
    ├── default/maestro.db          # Default workspace
    └── {workspace-id}/maestro.db   # Additional workspaces
```

The database is created automatically on the first run. Each workspace has its own file, ensuring complete data isolation.

## Code structure

```
maestro_local/
├── __main__.py              # Entry point: init_db -> start_api -> QApplication
├── config.py                # Config JSON + workspace management
├── db/
│   └── models.py            # SQLAlchemy models + switch_db()
├── api/
│   ├── app.py               # FastAPI endpoints (all resources)
│   └── server.py            # Uvicorn runner in a daemon thread
├── gui/
│   ├── theme.py             # ThemeColors dataclass + dark/light + stylesheet
│   ├── main_window.py       # MainWindow + sidebar + pomodoro + workspace selector
│   ├── workspace_selector.py # Workspace selector with emoji/color/description
│   └── views/
│       ├── daily_view.py        # My Day + Obsidian sync + report
│       ├── todos_view.py        # Simple TODO list
│       ├── chat_view.py         # Assistant (internal agent)
│       ├── transcricoes_view.py # Transcriptions (recording + transcription)
│       ├── settings_view.py     # Settings (AI, pomodoro, notifications)
│       ├── dashboard_view.py    # Dashboard with summary and activity
│       ├── study_view.py        # Study plans + topics + sessions
│       ├── board_view.py        # Kanban board + TaskCard + filters
│       ├── task_detail_dialog.py # Complete task dialog
│       ├── projects_view.py     # List/creation of projects
│       ├── labels_view.py       # Label CRUD with palette
│       ├── metrics_view.py      # Metrics dashboard
│       ├── skills_view.py       # Skills for AI agents
│       └── guide_view.py        # Usage instructions
├── ai/
│   ├── providers.py         # OpenAI-compatible providers + connection test
│   ├── tools.py             # Internal agent tools (board, review, TODOs)
│   └── agent.py             # Strategic agent (LangGraph ReAct)
├── transcricoes/
│   ├── audio.py             # Linux audio capture (parec/PipeWire)
│   ├── transcriber.py       # faster-whisper in a QThread
│   ├── summarizer.py        # Summarization via the Maestro provider
│   ├── assistants.py        # Meeting and study assistants
│   ├── markdown_gen.py      # Markdown generation for the summaries
│   └── hotkeys.py           # Global shortcuts (pynput)
└── skills/
    └── catalog.py           # Catalog of 12 skills with SKILL.md content
```

## Requirements

- Python 3.10+
- Qt 6 (installed automatically with PySide6)
- `langgraph` + `langchain-openai` (installed automatically; used by the Assistant)
- For the Chat and the analysis of Transcriptions: an OpenAI-compatible AI provider (local LM Studio, opencode, etc.)
- For Transcriptions (recording on Linux): `pulseaudio-utils` (`parec`/`pactl`) and PipeWire/PulseAudio; `faster-whisper` for transcription (installed automatically)
- Linux, macOS, or Windows
