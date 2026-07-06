> 🇧🇷 [Versão em português](TODO.ptbr.md)

# Next steps — Agentic Dev Maestro

Living backlog of upcoming work. Items at the top have priority. Effort in
person-days (pd) is an estimate; staffing/scheduling is up to leadership.

---

## 🔴 Priority

### 1. Improve the TODOs module (scheduling + in-app reminders) — MAIN

Today a TODO is minimal (text + done). Make it more explicit and add
**scheduling** with **periodic in-app notifications**.

**Data model**
- [ ] Add to `Todo`: `due_at` (scheduled date/time), and optionally `priority`,
  `notes`, `remind` (toggles the reminder). Additive light migration
  (`ALTER TABLE todos ADD COLUMN ...`), following the existing `init_db` pattern.

**API**
- [ ] Create/update a TODO with `dueAt` (and the other fields).
- [ ] Endpoint to list **pending/overdue** TODOs (`due_at <= now` and
  `done = false`), used by the notification mechanism.

**UI (desktop + web)**
- [ ] Date/time picker per TODO; show the scheduled time.
- [ ] Visual states: scheduled, **overdue/pending**, done.
- [ ] Sort/filter by time and by pending status.

**In-app notifications (in-app only — no OS notifications)**
- [ ] When a TODO's scheduled time is reached, the app starts showing a
  **periodic reminder** (e.g. a toast/banner every N minutes) indicating there
  are pending tasks, with a **count** of overdue items.
- [ ] Reminder actions: **complete**, **snooze** for X min, and **dismiss**
  until the next cycle.
- [ ] Desktop: a `QTimer` polling for pending items + a toast/banner widget
  (reuse the existing in-window notification pattern).
- [ ] Web: a polling interval against the pending endpoint + a toast in the UI.
- [ ] A pending/overdue badge visible in the navigation (e.g. on the TODOs item).

**Acceptance criteria**
- A TODO scheduled for a time starts **reminding periodically** in the UI after
  that time, until it is completed or snoozed.
- The pending/overdue count is visible.
- Nothing triggers an OS notification — everything stays inside the app.

---

## 🟡 Backlog — new modules (help developers day-to-day)

Ideas that fit the architecture (reuse the AI provider, board/API, per-workspace
SQLite, DevLog/comments, MCP).

- [ ] **Password manager (KeePass-compatible)** (~4–5 pd) — a **local**
  credentials/secrets vault that reads and writes the **`.kdbx`** format
  (KeePass 2.x, via `pykeepass`), unlocked by a **master password** and/or key
  file. Interoperates with existing KeePass vaults; search, organization by
  groups and **copy-to-clipboard with auto-clear**. Always **local and
  encrypted**; the master password is never persisted (vault locks on
  inactivity). Extra security care since it handles credentials.
- [ ] **Git/PR cockpit** (~4–6 pd) — current branch, uncommitted changes,
  commits and PRs (`git`/`gh`); link branch/commit → task (DevLog already has
  `COMMIT_REF`/`DEPLOY_LOG`); AI suggests a commit message / PR description.
- [ ] **Time tracking + Pomodoro per task** (~2–3 pd) — a timer on a task →
  logs time → feeds real cycle time into Metrics + a weekly timesheet.
- [ ] **Snippets & prompt library** (~2 pd) — reusable code snippets and AI
  prompts (with variables), searchable by label (SQLite + FTS).
- [ ] **Knowledge base (second brain)** (~4 pd) — per-project notes/wiki with
  backlinks and AI Q&A over your notes (RAG over the workspace); reuses `Document`.
- [ ] **Bug intake/triage** (~2 pd) — quick capture (paste a stack trace) → AI
  classifies severity/type → becomes a task (`bug-triage` skill).
- [ ] **Sprint retrospective** (~2 pd) — on sprint completion, "what went
  well/badly/actions" with AI; actions become tasks.
- [ ] **API tester (mini-Postman)** (~3 pd) — save requests per project, run
  them and keep a history.
- [ ] **Proactive digest (automatic standup)** (~3 pd) — "done/doing/blockers"
  from board activity + commits + Daily Note; weekly summary.
- [ ] **Import TODO/FIXME from code** (~1–2 pd) — scan the repo for `TODO/FIXME`
  comments and import them as tasks linked to the file.
- [ ] **Code review assistant** (~3 pd) — point at a diff/branch → AI review →
  posted as a `CODE_REVIEW` comment on the task.
- [ ] **Project runbooks/commands** (~2 pd) — setup/deploy/command cards with
  one-click copy; AI generates them from the README.

---

## 📝 Conventions
- Docs in English (`*.md`) with a PT version in `*.ptbr.md`.
- Schema migrations are additive and idempotent (see `_run_light_migrations`).
- New modules should also be exposed via the API/MCP when it makes sense.
