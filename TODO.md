> 🇧🇷 [Versão em português](TODO.ptbr.md)

# Next steps — Agentic Dev Maestro

Living backlog of upcoming work. Items at the top have priority. Effort in
person-days (pd) is an estimate; staffing/scheduling is up to leadership.

---

## ✅ Done

### 1. Improve the TODOs module (scheduling + in-app reminders) — MAIN ✅

TODOs are now schedulable with periodic in-app reminders (desktop + web).

- [x] `Todo`: added `due_at`, `priority`, `notes`, `snoozed_until` (additive
  light migration in `_run_light_migrations`).
- [x] API: create/update with `dueAt`/`priority`/`notes`; `GET /api/todos/pending`
  (overdue & not snoozed); `POST /api/todos/{id}/snooze`. Scheduling uses local time.
- [x] UI (desktop + web): date/time picker + priority per TODO; overdue is
  highlighted in red.
- [x] In-app notifications (in-app only): a periodic reminder (every 1 min) with
  a **count**, and **View / Snooze 10min / Dismiss** actions. Desktop via a
  `QTimer` + bottom banner; web via a polling toast in the app shell.
- [x] Snooze silences the reminder for 10 min; dismiss hides until the next cycle.
- [x] Pending badge (⏰N) on the nav item (desktop: Dashboard item; web: TODOs item).
- [x] Inline editing of priority, recurrence and due date on each row
  (set/clear schedule included).
- [x] Recurring TODOs (daily/weekly/monthly): completing a recurring TODO
  reschedules it to the next future occurrence instead of marking it done.

---

## 🟡 Backlog — new modules (help developers day-to-day)

Ideas that fit the architecture (reuse the AI provider, board/API, per-workspace
SQLite, DevLog/comments, MCP).

- [x] **Password manager (KeePass-compatible)** (~4–5 pd) — a **global**
  credentials/secrets vault (one for the whole app, **not per workspace**; kept
  outside the per-workspace databases, e.g. a single `.kdbx` in the config dir).
  Reads and writes the **`.kdbx`** format (KeePass 2.x, via `pykeepass`),
  unlocked by a **master password** and/or key file. Interoperates with existing
  KeePass vaults; search, organization by groups and **copy-to-clipboard with
  auto-clear**. Always **local and encrypted**; the master password is never
  persisted (vault locks on inactivity). Extra security care since it handles
  credentials.
- [x] **Git/PR cockpit** (~4–6 pd) — current branch, ahead/behind, uncommitted
  changes (staged/unstaged/untracked), recent commits and open PRs (`git`/`gh`,
  read-only). API `/api/git/status`; "Git" tab in the Library (desktop + web).
- [x] **Time tracking + Pomodoro per task** (~2–3 pd) — a stopwatch (+ manual
  entry) logs time optionally against a task; weekly total and per-task
  breakdown. API `/api/timelogs`; "Time" tab in the Library (desktop + web).
- [x] **Snippets & prompt library** (~2 pd) — reusable code snippets and AI
  prompts, searchable by text/tags/language. Desktop **Library** view + web
  `/biblioteca`; API `/api/snippets`. Kind SNIPPET|PROMPT, copy-to-clipboard,
  use counter.
- [ ] **Knowledge base (second brain)** (~4 pd) — per-project notes/wiki with
  backlinks and AI Q&A over your notes (RAG over the workspace); reuses `Document`.
- [x] **Bug intake/triage** (~2 pd) — quick capture (paste a stack trace) → AI
  classifies severity/type/title (+ probable cause and steps) → becomes a BUG
  task. API `/api/bugs/triage`; "Bug triage" tab in the Library (desktop + web).
- [x] **Sprint retrospective** (~2 pd) — per sprint, AI generates "what went
  well/badly/actions" (stored on the sprint); actions become CHORE tasks. API
  `/api/sprints/{id}/retrospective` (+ `/actions`); "Retrospective" button in the
  Sprint Planning tab (web) and the Sprint manager dialog (desktop).
- [x] **API tester (mini-Postman)** (~3 pd) — build/run/save HTTP requests and
  keep an execution history. API `/api/http-requests` (+ `/run`, `/history`);
  dedicated screen on desktop and web (`/api-tester`).
- [x] **Proactive digest (automatic standup)** (~3 pd) — AI "done/doing/blockers"
  + summary from board state, recent activity and Daily Notes. API `/api/digest`;
  "Digest (standup)" card on the Dashboard (desktop + web).
- [x] **Import TODO/FIXME from code** (~1–2 pd) — scan a folder for
  `TODO/FIXME/HACK/XXX` and import selected ones as tasks linked to the file.
  API `/api/code/scan-todos` + `/api/code/import-todos`; "Import from code" tab
  in the Library (desktop + web).
- [x] **Code review assistant** (~3 pd) — point at a repo + base (branch/ref) →
  AI reviews the git diff (summary, issues by severity, suggestions), optionally
  posted as a `CODE_REVIEW` comment on a task. API `/api/code/review`;
  "Code review" tab in the Library (desktop + web).
- [x] **Project runbooks/commands** (~2 pd) — setup/deploy/command cards with
  one-click copy. Desktop **Library** "Runbooks" tab + web `/biblioteca`; API
  `/api/runbooks` (category, use counter).

---

## 📝 Conventions
- Docs in English (`*.md`) with a PT version in `*.ptbr.md`.
- Schema migrations are additive and idempotent (see `_run_light_migrations`).
- New modules should also be exposed via the API/MCP when it makes sense.
