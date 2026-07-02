> 🇧🇷 [Versão em português](09-modulo-estudos.ptbr.md)

# 09 — Studies Module

## Context

Maestro today handles development task tracking. The idea is to expand it so it also works as a personal study tracking tool — allowing you to define a learning roadmap, break it into topics/stages, track percentage progress and keep study notes integrated into the existing flow.

The goal is not to create a separate app, but to integrate studies as a module within Maestro, reusing as much of the existing infrastructure as possible (projects, tasks, kanban, daily notes, Obsidian).

---

## Main concepts

### Study Plan (StudyPlan)

A study plan is a container that represents a complete journey — e.g.: "Learn Rust", "AWS SAA Certification", "Algorithms and Data Structures".

Each plan has:
- **Title** and **description**
- **Category** (language, framework, certification, concept, course, book)
- **Status** (planned, in progress, paused, completed, abandoned)
- **Start date / target date** (optional, for personal deadlines)
- **Overall progress** (calculated automatically from the topics)
- **Resources** (links, books, courses — free-form list)
- **Linked project** (optional — can be linked to an existing Maestro project to use the kanban)

### Study Topic (StudyTopic)

Each plan is divided into ordered topics that make up the roadmap. A topic can have sub-topics (1-level hierarchy).

Each topic has:
- **Title**
- **Description** (what to cover, why it matters)
- **Order** in the roadmap
- **Status** (pending, studying, review, completed, skipped)
- **Weight** (default 1 — allows giving more importance to larger topics)
- **Hours estimate** (optional)
- **Logged hours** (time tracking)
- **Notes** (free-form markdown — study notes)
- **Resources** (topic-specific links)
- **Parent** (for sub-topics)

### Study Session (StudySession)

A record of when the user sat down to study. Can be manual or with a timer.

- **Linked topic**
- **Start and end date/time**
- **Duration** (minutes)
- **Session notes** (what was learned, questions, insights)
- **Confidence level** (1-5: how well the topic was understood)

---

## Progress calculation

The plan's percentage progress is calculated based on the topics:

```
progresso = soma(peso dos topicos concluidos) / soma(peso de todos os topicos) * 100
```

Topics with status "skipped" do not count in the denominator (they were removed from scope).

Sub-topics contribute proportionally to the weight of the parent topic:
- If a parent topic has weight 3 and 2 of 4 sub-topics are completed, it contributes 1.5 (3 * 0.5).

---

## Data model

```
StudyPlan
  id            INTEGER PK
  title         VARCHAR(200) NOT NULL
  description   TEXT
  category      VARCHAR(40)   -- linguagem, framework, certificacao, conceito, curso, livro
  status        VARCHAR(20)   -- planejado, em_andamento, pausado, concluido, abandonado
  start_date    DATE
  target_date   DATE
  resources     TEXT          -- JSON array de {title, url, type}
  project_id    INTEGER FK    -- opcional, vinculo com Project existente
  created_at    DATETIME
  updated_at    DATETIME

StudyTopic
  id            INTEGER PK
  plan_id       INTEGER FK -> StudyPlan
  parent_id     INTEGER FK -> StudyTopic (nullable, para sub-topicos)
  title         VARCHAR(200) NOT NULL
  description   TEXT
  sort_order    INTEGER
  status        VARCHAR(20)   -- pendente, estudando, revisao, concluido, pulado
  weight        FLOAT DEFAULT 1.0
  estimate_hours FLOAT
  logged_hours  FLOAT DEFAULT 0
  notes         TEXT          -- markdown
  resources     TEXT          -- JSON array
  created_at    DATETIME
  updated_at    DATETIME

StudySession
  id            INTEGER PK
  topic_id      INTEGER FK -> StudyTopic
  plan_id       INTEGER FK -> StudyPlan
  started_at    DATETIME
  ended_at      DATETIME
  duration_min  INTEGER
  notes         TEXT
  confidence    INTEGER       -- 1 a 5
  created_at    DATETIME
```

---

## Interface (GUI)

### New page: "Studies" in the sidebar

Position in the menu: between "Journal" and "Board" (Alt+2).

### Main screen: list of plans

- Cards with title, category, status, percentage progress bar
- Filters by status and category
- "New Plan" button
- Sorting by last accessed, progress, target date

### Plan screen: visual roadmap

- Header with title, description, overall progress (bar + percentage)
- Statistics: completed/total topics, estimated vs. logged hours
- List of topics as a vertical timeline/roadmap:
  - Each topic shows: title, status (colored badge), progress bar (sub-topics), hours
  - Topic expandable to see sub-topics and notes
  - Drag-and-drop to reorder
- Side panel or dialog to edit a topic:
  - Title, description, notes (markdown), resources
  - Status (dropdown)
  - Study session logging ("Log session" button)
- "Start session" button (simple timer)

### Study session screen

- Timer (optional — can be logged manually)
- Notes field (markdown)
- Confidence slider (1-5)
- On finish: saves the session and updates the topic's hours

### Journal integration

- On the "Work Journal" page, show the day's study sessions
- In the generated report, include a "Studies" section with:
  - Sessions performed
  - Study hours
  - Topics advanced

### Obsidian integration

On vault synchronization, export:
```
Vault/
  Estudos/
    NomePlano/
      README.md          -- overview, progresso, recursos
      Roadmap.md         -- lista de topicos com status
      Topicos/
        01-TopicA.md     -- notas do topico
        02-TopicB.md
      Sessoes/
        2026-06-25.md    -- sessoes do dia
```

### Project integration (optional)

If the plan is linked to a project:
- Each topic can generate a task on the kanban (manual "Create task" action)
- The task keeps a reference to the topic
- Completing the task marks the topic as completed

---

## API endpoints

```
GET    /api/study/plans                    -- listar planos
POST   /api/study/plans                    -- criar plano
GET    /api/study/plans/:id                -- detalhe do plano (com topicos)
PATCH  /api/study/plans/:id                -- atualizar plano
DELETE /api/study/plans/:id                -- remover plano

GET    /api/study/plans/:id/topics         -- listar topicos do plano
POST   /api/study/plans/:id/topics         -- criar topico
PATCH  /api/study/topics/:id               -- atualizar topico
DELETE /api/study/topics/:id               -- remover topico
PATCH  /api/study/plans/:id/topics/reorder -- reordenar topicos

POST   /api/study/sessions                 -- registrar sessao
GET    /api/study/sessions?date=YYYY-MM-DD -- sessoes por data
GET    /api/study/plans/:id/sessions       -- sessoes do plano

GET    /api/study/stats                    -- estatisticas gerais (horas, planos ativos, streak)
```

---

## Implementation phases

### Phase 1 — Foundation (MVP)
- SQLAlchemy models: StudyPlan, StudyTopic, StudySession
- Database migration
- Basic CRUD endpoints
- "Studies" page in the sidebar with a list of plans
- Plan creation/editing screen
- List of topics with status and reordering
- Progress calculation

### Phase 2 — Sessions and tracking
- Study session logging (manual)
- Simple timer (optional)
- Logged hours per topic
- Confidence slider
- Journal integration (show the day's sessions in the report)

### Phase 3 — Visualization and polish
- Visual roadmap (vertical timeline)
- Progress-over-time charts
- Study streak (consecutive days)
- Statistics on the Metrics page
- Obsidian integration (export of plans and notes)

### Phase 4 — Project integration
- Link a plan to a project
- Generate tasks from topics
- Sync topic <-> task status

---

## Open decisions

1. **Timer**: implement a real timer (with notification) or just manual hour logging?
2. **Gamification**: add streaks, badges, XP? It can motivate but also adds complexity.
3. **Roadmap import**: allow pasting a roadmap in markdown and automatically parsing it into topics?
4. **Flashcards/spaced repetition**: does it make sense to integrate spaced repetition (Anki-style) into topics? It could be a future module.
5. **Sharing**: export a plan as a template to reuse? E.g.: a "Rust Roadmap" that anyone can import.
