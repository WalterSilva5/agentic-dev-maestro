# 13 — Flutter front-end implementation plan

> Goal: rewrite the `local-client` UI in **Flutter**, keeping the **Python
> backend** as a local daemon (API + WebSocket). Everything Flutter does not
> support well (system audio capture, offline Whisper, KeePass, global
> shortcuts, the AI layer) **stays in Python** and is exposed over the API.
>
> This document is the execution plan: tasks, subtasks and roadmap. Effort in
> **person-days (PD)**; allocation and scheduling are a leadership call.
>
> Starting decision: [Plan 11 — UI toolkit](migracao-toolkit-ui.md) recommended
> the web route; the call was made for **Flutter**, and this plan details that
> option's execution (section 8 records what changes versus Plan 11).

## 1. Measured situation (the plan's baseline)

Gathered from the code, not estimated:

| Item | Measure |
|---|---|
| Flutter toolchain | **3.44.6 stable**, Dart 3.12.2, Linux desktop **already enabled** |
| Existing Flutter project | **None** (greenfield) |
| API endpoints | **127** (47 GET, 45 POST, 17 DELETE, 11 PATCH, 7 PUT) |
| OpenAPI contract | **3.1.0**, 91 paths, 54 schemas — **Dart client can be generated** |
| Authentication | **None**; workspace is **global server state** (`POST /api/workspaces/active`) |
| Qt screens | 21 views, **13,286 LOC** |
| React web UI (ready reference) | 16 screens, **3,249 LOC** |
| **No API coverage** | **Meetings** (Whisper settings only) and **Vault** (KeePass) |

Two facts shape the plan:

1. **OpenAPI covers almost everything.** 91 typed paths allow **generating** the
   Dart client + models instead of hand-writing them. Big cost and
   contract-drift reduction.
2. **Meetings has no API at all.** It is the only large feature 100% bound to Qt
   (audio capture + Whisper + live state). It is the largest **backend** block
   in this plan — and must exist before the Flutter screen.

## 2. Target architecture

```
┌────────────────────────────────────────┐
│  Flutter (UI)                          │   Linux desktop (mobile: later)
│  · screens, navigation, state          │
│  · client generated from OpenAPI       │
└──────────────┬─────────────────────────┘
               │  HTTP + WebSocket (127.0.0.1:9777)
┌──────────────▼─────────────────────────┐
│  Python daemon (FastAPI + uvicorn)     │   single source of truth
│  · 127 endpoints + live WS             │
│  · per-workspace SQLite                │
│  · audio capture (parec/PulseAudio)    │ ← native, stays in Python
│  · offline Whisper (ctranslate2)       │ ← native, stays in Python
│  · LangChain/LangGraph (AI)            │ ← stays in Python
│  · KeePass, global hotkeys, capture    │ ← native, stays in Python
└────────────────────────────────────────┘
```

**Cut rule:** Flutter only draws and navigates. Anything touching audio, a local
model, the user's filesystem or an AI provider stays in the daemon and becomes
an endpoint.

## 3. What stays in Python (and why)

| Capability | Why it does not move to Flutter |
|---|---|
| **System audio capture** | `parec`/PulseAudio captures *other apps'* audio. Dart audio packages cover the microphone, not loopback/monitor sources on Linux. |
| **Whisper transcription** | faster-whisper/ctranslate2 is C++ with a Python binding. Porting to Dart FFI is costly and fragile. |
| **AI layer** | LangChain/LangGraph + `ai/llm.py` (structured output, fallback, caches) already solved in Python. |
| **KeePass vault** | `pykeepass`. Re-implementing crypto handling in Dart is unnecessary risk. |
| **Global shortcuts** | `pynput`. Flutter's global-shortcut support on Linux/Wayland is limited. |
| **Monitor capture** | The screen watcher uses Qt's screen API. Flutter desktop exposes no equivalent. |
| **Obsidian sync / skills install** | Writes to the user's filesystem, already implemented. |
| **Database (SQLite/SQLAlchemy)** | Source of truth; Flutter never talks to the DB directly. |

## 4. Phases, tasks and subtasks

Each item is a task; `·` bullets are subtasks.

### F0 — Foundation (~5–7 PD)

- [ ] **F0.1 — Create the Flutter project** (~0.5 PD)
  - · `flutter create` targeting Linux desktop; folder structure
    (`lib/{core,data,features,ui}`)
  - · Set the minimum Dart SDK and pin the Flutter version (avoids drift)
  - · Lint (`flutter_lints`) and formatting in the local CI
- [ ] **F0.2 — Generate the Dart client from OpenAPI** (~1.5 PD)
  - · Pick a generator (`openapi-generator` or `swagger_dart_code_generator`)
  - · `tools/gen_api_client.sh` that pulls `/openapi.json` from the daemon and
    regenerates — the contract is never hand-written
  - · Commit the generated client (reproducible builds) and document when to
    regenerate
  - · Thin layer on top (base URL, timeouts, uniform error handling)
- [ ] **F0.3 — State and navigation** (~1 PD)
  - · State management (recommended: **Riverpod**) and provider conventions
  - · Routing (**go_router**), routes mirroring the current screens
  - · Global state: active workspace, active project, theme
- [ ] **F0.4 — Design system** (~1.5 PD)
  - · Port the current theme: indigo accent `#4F46E5`, radius 12, soft shadows,
    Inter typography, light **and** dark
  - · Base components: card, button (primary/ghost), input, badge, empty state,
    numbered `SectionCard`, action grouping
  - · Real responsiveness (the original reason for migrating): breakpoints and
    adaptive layout from the start
- [ ] **F0.5 — App shell** (~1 PD)
  - · Sidebar navigation, workspace and project selectors
  - · Workspace switching calls `POST /workspaces/active` **with confirmation**
    (it is global daemon state — it swaps the active database)
  - · Theme toggle; status bar (API health)
- [ ] **F0.6 — End-to-end smoke** (~0.5 PD)
  - · Dashboard consuming the real API; visible error when the daemon is down
  - · Boot health check (`/api/health`) with a clear message

### F1 — CRUD screens over the existing API (~20–26 PD)

All consume endpoints that **already exist**. The React web UI is the functional
reference (3,249 LOC for 16 screens shows API-driven UI is lean).

Simple (~0.5–1 PD each):
- [ ] **F1.1 — Labels** · CRUD, color, per-task usage
- [ ] **F1.2 — Translator** · source/target, history
- [ ] **F1.3 — API tester** · request, response, saved history
- [ ] **F1.4 — Guide/Instructions** · static content + navigation
- [ ] **F1.5 — Tools hub** · grid of shortcuts to the extra screens

Medium (~1–1.5 PD each):
- [ ] **F1.6 — Dashboard** · summary, digest (AI), recent activity, projects
- [ ] **F1.7 — Projects** · list, create, delete, open board
- [ ] **F1.8 — TODOs** · scheduling, recurrence, snooze, pending badge
- [ ] **F1.9 — Metrics** · velocity, lead/cycle time (charts: `fl_chart`)
- [ ] **F1.10 — Studies** · plans, topics, create from file
- [ ] **F1.11 — Assistant (chat)** · streamed response, history
- [ ] **F1.12 — Library** · snippets and runbooks
- [ ] **F1.13 — Knowledge base + memory** · semantic search, ingestion
- [ ] **F1.14 — Settings** · language, AI providers, Whisper, notifications
- [ ] **F1.15 — Sprints and planning** · allocation, retrospective

Complex (~2–3 PD each):
- [ ] **F1.16 — Board (kanban)** · columns, **drag & drop** across columns,
  sprint filter, cards with type/priority/labels/assignee
  - · Drag & drop with visual feedback and optimistic reordering
  - · Error/rollback state if `POST /tasks/{code}/move` fails
- [ ] **F1.17 — Task detail** · description, checklist (DoD), typed comments,
  dependencies, labels, sprint, time tracking
- [ ] **F1.18 — My Day** · notes with markdown preview, template, daily report
  (AI), activity, Obsidian sync, backup

### F2 — Backend: expose what is missing (Python) (~11–13 PD)

Prerequisite for F3. **None of this is Flutter work** — it completes the daemon.

- [ ] **F2.1 — Meetings API (CRUD)** (~2 PD)
  - · Endpoints over the **already existing** `transcricoes/repository.py`
    (list, get, save, delete, archive, reorder)
  - · Pydantic schemas mirroring the repository dict
  - · API tests (the repository already has 9 unit tests)
- [ ] **F2.2 — Decouple the workers from Qt** (~3–4 PD) ⚠ **biggest technical risk**
  - · Rewrite `agent_service`, `live_assistant`, `transcriber` from `QThread` to
    plain `threading`/`asyncio`
  - · Measured reason: the spike recorded in
    [Plan 12](eficiencia-recursos.md#3-to-do-by-effort) showed that running the
    Qt loop on a dedicated thread (the arrangement the daemon would need)
    **caused a segfault** — a Qt thread-affinity violation. Taking Qt out of the
    audio path is the clean fix, not working around it.
  - · Keep the Qt GUI working during the transition (signal adapter)
- [ ] **F2.3 — Live WebSocket** (~3 PD)
  - · Channel for partial transcript + assistant state (plan/actions/decisions/
    questions) in real time
  - · Versioned protocol (documented message types)
  - · Reconnection and state recovery on reconnect
- [ ] **F2.4 — Vault API (KeePass)** (~2 PD) ⚠ **security decision**
  - · Exposing the vault over local HTTP needs care: unlocked session, lock
    timeout, **never** log a secret, and a judgement on whether the endpoint
    should exist at all
  - · Alternative to consider: keep the Vault in the Qt/Python app only and
    **not** port it to Flutter (smaller risk surface)
- [ ] **F2.5 — Screen watcher API** (~1 PD)
  - · List monitors, capture a frame on demand, toggle on/off
- [ ] **F2.6 — Global shortcuts** (~0.5 PD)
  - · Stay in the daemon (`pynput`); expose a "toggle recording" command over
    the API so Flutter can reflect the state

### F3 — Meetings in Flutter (~5–7 PD) — depends on F2

- [ ] **F3.1 — Meeting screen** (~3 PD)
  - · The 4-step flow already settled in Qt: 1 Prepare → 2 Record →
    3 Live assistant → 4 Result (see the
    [improvements plan](melhorias-reunioes.md))
  - · Flow progress indicator (equivalent to `FlowIndicator`)
  - · Single transcript field (locked while recording)
- [ ] **F3.2 — WebSocket consumption** (~1.5 PD)
  - · Real-time partial transcript; plan/tips/actions/decisions/questions tabs;
    ask-the-meeting
  - · Manual answers to questions preserved across re-analysis
- [ ] **F3.3 — History and reopening** (~1 PD)
  - · List, search, archive/delete, reorder
  - · Reopening shows saved items (incl. deriving from `summary_json` for old
    recordings)
- [ ] **F3.4 — Context and attachments** (~1 PD)
  - · Upload file/image as context; screen capture via F2.5

### F4 — Parity, packaging and migration (~4–6 PD)

- [ ] **F4.1 — Parity checklist** (~1 PD)
  - · Screen by screen against the Qt GUI; list what was consciously left out
- [ ] **F4.2 — Linux packaging** (~2 PD)
  - · Release build; package (AppImage/Flatpak) bundling the Python daemon
  - · Startup script: bring up daemon and UI, health check
  - · Autostart (already exists for the Qt app)
- [ ] **F4.3 — Coexistence during the transition** (~1 PD)
  - · Qt and Flutter side by side, same daemon and same database
  - · Document which to use for what until parity closes
- [ ] **F4.4 — Retire Qt** (~1–2 PD)
  - · Only once F4.1 closes; remove views and the PySide6 dependency
  - · Decide the fate of the **React web UI** (see section 7)

### F5 — Mobile (optional, out of initial scope)

- [ ] **F5.1 — Feasibility** · the daemon listens on `127.0.0.1` today; phone use
  requires exposing it on the network → **security decision** (authentication,
  TLS, pairing). Do not do it without that design.
- [ ] **F5.2 — Layout adaptation** · screens are born responsive in F0.4

## 5. Roadmap

```
F0 Foundation ──► F1 CRUD screens ──────────────────► F4 Parity ──► retire Qt
   (5–7 PD)        (20–26 PD)                           (4–6 PD)
                                                          ▲
F2 Backend (Python) ──► F3 Meetings in Flutter ──────────┘
   (11–13 PD)             (5–7 PD)
```

- **F0 blocks** everything else.
- **F1 and F2 run in parallel** — different codebases (Dart × Python), no mutual
  blocking.
- **F3 depends on F2** (no meetings API/WS, nothing to consume).
- **F4 closes** once F1 and F3 are complete.

**Estimated total: ~45–59 PD.**

Suggested milestones:
1. **M1 — "It runs"**: F0 complete; real Dashboard and Projects in Flutter.
2. **M2 — "Usable daily"**: simple + medium F1 plus Board and Task detail.
3. **M3 — "Meetings work"**: F2 + F3.
4. **M4 — "Replaces Qt"**: F4 closed.

## 6. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| **Qt thread affinity** (F2.2) | High — segfault already observed in a spike | Remove Qt from the audio path (plain threading), do not work around it |
| **Board drag & drop** in Flutter | Medium | Prototype early in F1.16; optimistic rollback if the API fails |
| **API↔UI contract drift** | Medium | **Generated** client from OpenAPI + versioned regeneration (F0.2) |
| **Vault over HTTP** (F2.4) | High (security) | Consider not porting; if ported, session with timeout and no secret logging |
| **Three front ends at once** (Qt + React + Flutter) | Medium (maintenance cost) | Decide the React fate in F4.4; migrate one screen at a time |
| **Estimate above Plan 11** | Low | See section 8 — the delta is the Meetings backend, previously under-costed |

## 7. Decision points

- **Fate of the React web UI**: keep as browser/remote access, or retire it with
  Qt? Three front ends are expensive; keeping two (Flutter desktop + React
  remote) only if browser access has real value.
- **Vault in Flutter**: port it (requires a vault API) or leave it out of scope?
  Recommendation: **leave it out** in the first cycle — smaller risk surface.
- **Mobile**: only after solving daemon authentication/exposure (F5.1).

## 8. Relation to Plan 11

[Plan 11](migracao-toolkit-ui.md) estimated the Flutter route at **~27–50 PD**
and recommended the web route. The call was Flutter; this plan details the
execution and lands at **~45–59 PD**. The difference is not a UI re-estimate —
Plan 11 treated the audio *sidecar* as a single item (~3–5 PD), whereas here the
Meetings backend (F2) is broken into 6 tasks (~11–13 PD), including the **Qt
decoupling** whose real difficulty only became clear in the spike recorded in
[Plan 12](eficiencia-recursos.md).

Still true from Plan 11: **audio capture and Whisper stay in Python in every
scenario** — swapping the UI toolkit does not remove that part.
