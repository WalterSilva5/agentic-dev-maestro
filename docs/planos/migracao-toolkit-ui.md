# 11 — UI toolkit decision: Flutter vs Java vs web route

> Goal: decide which technology to migrate the `local-client` UI to — currently
> **PySide6/Qt6** — aiming for a **modern** look and leaving Qt behind. This
> document states the constraint that dominates the decision, compares the
> options (Flutter, Java, web route) and breaks the work down by tasks, with
> effort in **person-days (PD)**. Allocation and scheduling are a leadership call.
>
> Complements [Plan 10 — responsive front-end](migracao-frontend-responsivo.md),
> which already recommended the web route; here the comparison is reopened on
> request to explicitly include **Flutter** and **Java**, with an execution plan
> for whichever path is chosen.

## 1. The constraint that dominates the decision

The **Meetings** screen depends on two capabilities that **only exist in a
native/local process**:

1. **System audio capture** — `parec`/PulseAudio (later, a PipeWire portal on
   Wayland). The browser cannot capture other apps' audio.
2. **Offline transcription** — faster-whisper/ctranslate2, running in the local
   process.

Core consequence: **no toolkit choice removes this part.** In Flutter, Java or
web, audio and Whisper stay in a native helper — today the Python process
itself. So the UI decision is **not** about "who solves audio"; it is about
**rewrite cost** and **visual quality ceiling**, keeping the capture/AI core
where it already works (Python).

## 2. The real starting point (what already exists)

- **Current desktop**: `local-client` in PySide6/Qt6 + embedded **FastAPI** (9777).
- **Web UI**: **React 18 + Vite** (`local-client/webui/`) with **16 working
  screens**, served by the API itself. A modern front end **already in place**.
- **Desktop shell**: `maestro_local/desktop_shell.py` (**pywebview**) already
  opens the web UI in a native window (Plan 10's E1, done).
- **UI-agnostic layers** recently extracted and reusable by any front via the
  API: `transcricoes/repository.py` (persistence), `transcricoes/agent_service.py`
  (AI orchestration), `transcricoes/session.py` (`MeetingSession`). The daemon
  logic is **already decoupled from the Qt UI**.
- **Gap**: **Meetings** is the only large screen still Qt-only (because of the
  section 1 constraint). English practice and the KeePass vault are desktop-only
  by nature.

## 3. Options

### Option F — Flutter (desktop + mobile)
- **How**: rewrite the ~16 screens in Flutter Desktop; audio/Whisper stay in a
  **Python sidecar** reached over local API/WebSocket (or native/FFI plugins for
  PulseAudio and ctranslate2 — costlier and more fragile). The AI layer (Python)
  stays a service.
- **Pros**: modern, responsive toolkit; **one codebase for desktop and mobile**;
  rich components and animation.
- **Cons**: **full UI rewrite**; **discards** the React + FastAPI investment (the
  16 finished screens); new language (Dart) and toolchain; the audio/live-state
  bridge must be rebuilt for Dart↔Python. It is the **most expensive** option.
- **Gain over web**: real native mobile and native components; for **desktop**,
  the visual gain over a well-styled web UI is small.

### Option J — Java (Swing/JavaFX)
- **How**: rewrite the UI in Swing or JavaFX; audio/Whisper stay in a Python
  sidecar (Java has no practical native PulseAudio/ctranslate2).
- **Pros**: robust JVM; smaller curve if the team already knows Java.
- **Cons**: **Swing is dated** (2000s aesthetics) and **JavaFX is heavy and also
  dated** next to web/Flutter. **Does not meet the "modern" goal** — likely a
  visual regression versus the current web UI. Also a full rewrite that discards
  the React/FastAPI investment.
- **Verdict**: **not recommended** for the stated goal (modern interface).
  Documented here only to record the comparison.

### Option W — Web route (existing React) + native shell
- **How**: consolidate on the React web UI that **already exists**; the Python
  app becomes a **local daemon** (capture + Whisper + AI) exposing **API +
  WebSocket**; wrap it in a native shell (**pywebview** already done; **Tauri**
  as an evolution for a smaller binary/tray/global shortcut).
- **Pros**: **reuses everything** (React + FastAPI + the already-extracted
  agnostic layers); real responsiveness (CSS/flex/grid); heavy logic stays where
  it works; **incremental** migration (one screen at a time, almost all done).
- **Cons**: live Meetings needs **WebSocket streaming**; screen watcher/capture
  stay native in the daemon; "app feel" depends on the shell (pywebview/Tauri).
- **Cost**: **the lowest** — most of it is wiring React screens to endpoints/WS.

## 4. Comparison (summary)

| Criterion | F — Flutter | J — Java (Swing/JavaFX) | W — Web route |
|---|---|---|---|
| Visual modernity (desktop) | High | Low/Medium | High |
| Native mobile | Yes | No (practical) | PWA/responsive |
| Reuses React + FastAPI | No | No | **Yes** |
| Reuses agnostic layers (repo/agent/session) | Via API | Via API | **Direct/Via API** |
| Solves audio/Whisper without Python | No | No | No |
| Rewrite cost | **Very high** | High | **Low/Medium** |
| New language/toolchain | Dart | — | — |

## 5. Recommendation

1. **Web route (W)** remains the technical recommendation: same desktop visual
   ceiling as Flutter, far lower cost, and it reuses what already exists. The
   "app feel" comes from the shell (pywebview today; Tauri as the next step).
2. **Flutter (F)** only if **native mobile** is a first-class product
   requirement — then the gain justifies the rewrite. For desktop-only, it does
   not pay off.
3. **Java (J)**: ruled out for the modern-interface goal.

## 6. Execution plan — Web route (W), recommended

Phases by tasks and objectives; effort in PD.

- **W0 — Native shell as default** (~1 PD): make pywebview the recommended way to
  open the app (document in README/install); Meetings opens the legacy Qt window
  until W2/W3 land.
- **W1 — Live streaming in the API** (~3–5 PD): expose transcription and live
  state (items/plan/questions) over **WebSocket**, consuming the existing
  `agent_service`/`session`.
- **W2 — Meetings on the web** (~5–8 PD): recreate the screen in React consuming
  the WS + endpoints (preparation, context, workspace/project, Q&A, result).
  Parity with the Qt screen.
- **W3 — Headless capture/Whisper daemon** (~2–3 PD): run capture + Whisper
  without the Qt GUI, as a service of the API process.
- **W4 — Parity and Qt retirement** (~3–5 PD + as scoped): migrate the remaining
  screens and disable the Qt GUI once parity is reached; decide Tauri vs
  pywebview for final packaging.

**Estimated total (W): ~14–21 PD**, excluding incremental screen polish.

## 7. Execution plan — Flutter (F), if chosen

Only if the product requires native mobile. Effort in PD.

- **F0 — Proof of concept** (~2–3 PD): minimal Flutter Desktop app consuming the
  current FastAPI (one screen: Dashboard) to validate the HTTP/WS bridge.
- **F1 — Audio/AI sidecar** (~3–5 PD): define the Dart↔Python contract
  (API/WebSocket) for capture, Whisper and live state; keep the core in Python
  (FFI for PulseAudio/ctranslate2 stays research, not the baseline).
- **F2 — Flutter design system** (~3–5 PD): theme, base components (cards,
  navigation, forms) equivalent to what the web already has.
- **F3 — Screen rewrite** (~1–2 PD per screen × 16 ≈ 16–32 PD): port each screen
  consuming the API; Meetings consumes F1's WS.
- **F4 — Packaging** (~3–5 PD): desktop build (Linux/Windows) and, if applicable,
  mobile; distribution.

**Estimated total (F): ~27–50 PD**, plus re-solving the audio bridge outside the
Python ecosystem. It is the **most expensive** path.

## 8. Risks and decision points

- **Native audio**: in every option capture stays in the Python daemon
  (parec/PulseAudio; PipeWire later). Neither a browser nor a Flutter/Java front
  can capture system audio without a native helper.
- **Cost of two front ends** during the transition: mitigated by migrating **one
  screen at a time** and keeping the API as the single source of truth.
- **Packaging** (web route): pywebview (done, pure Python) vs Tauri (smaller
  binary, tray/global shortcut) — a W4 decision.
- **Dart/Flutter** (F route): new toolchain and language; the weight of
  rewriting the 16 screens already built in React.

## 9. Decision

- [ ] **W — Web route** (was the technical recommendation): consolidate on the
  React web UI + Python daemon (WS) + native shell (pywebview → Tauri).
- [x] **F — Flutter** — **chosen**: rewrite the UI in Flutter, keeping the Python
  backend as a daemon. The detailed execution plan is
  [Plan 13 — Flutter front end](frontend-flutter.md) (~45–59 PD).
- [x] **J — Java**: ruled out (does not meet the modern-interface goal).

> Call made by the project owner. The technical recommendation recorded above was
> the web route (lower cost), but Flutter was chosen deliberately; section 7 of
> this document is the basis for Plan 13.
