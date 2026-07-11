# 10 — Responsive front-end plan (Meetings and beyond)

> Goal: make the UI (especially **Meetings**) genuinely responsive and decide
> whether it's worth migrating from PySide6/Qt to another technology (Flutter,
> web…). This document frames the problem, weighs the options, and recommends a
> path. Effort is estimated in **person-days (PD)**; staffing/schedule is a
> leadership decision.

## 1. Current context

- **Desktop**: `local-client` in **PySide6/Qt6** (GUI) + embedded **FastAPI** (port 9777).
- **Web**: there is already a **React 18 + Vite web UI** (`local-client/webui/`),
  served by the API itself — i.e. **a responsive front already exists in the project**.
- **AI layer**: LangChain/LangGraph over OpenAI-compatible endpoints (`ai/llm.py`).
- **Meetings** is **desktop-only** for two technical reasons:
  1. **System-audio** capture via `parec`/PulseAudio (a browser can't access other
     apps' audio);
  2. **Offline transcription** with faster-whisper (runs in the local process).

## 2. Problem

Qt has no declarative responsive layout model (no media queries/CSS). Everything is
manual: `QSplitter`, size policies, minimum widths. As the Meetings screen grew
(preparation, context, screen watcher, workspace/project selectors), its components
started to **break at smaller widths** (overlapping items, clipped buttons, no scroll).

## 3. Fixes already applied (short term, Option A)

Without switching stacks, the Meetings screen got:

- **Vertical scroll** for the content column (`QScrollArea`) — nothing overlaps anymore.
- **`FlowLayout`** on the action bars (buttons/combos wrap to the next line).
- **Breakpoint**: below ~820px the **history panel collapses** and hides, with a
  "☰ History" button to bring it back; the content then uses the full width.
- **Relaxed minimum widths** (right column, combos) and a minimum height for the live
  panel, preventing the inner splitter from being clipped.

This resolves the immediate symptoms. `FlowLayout` and the breakpoint pattern are
**reusable** across the other desktop screens.

## 4. Medium/long-term options

### Option A — Stay on Qt, make it responsive
- **How**: apply `FlowLayout` + breakpoints (collapsing panels) + `QScrollArea` to the
  remaining screens; extract a shared "responsiveness" utility.
- **Pros**: no new stack; keeps native audio capture and Whisper; incremental.
- **Cons**: responsiveness in Qt is always manual/verbose; lower visual ceiling than
  web/Flutter.
- **Effort**: ~1 PD per screen (most infrastructure already exists).

### Option B — Migrate the desktop to **Flutter**
- **How**: rewrite the UI in Flutter Desktop; audio capture and Whisper would need
  **native plugins/FFI** (PulseAudio/PipeWire, ctranslate2) or would stay in a Python
  process accessed via the local API; the (Python) AI layer would remain a service.
- **Pros**: modern, responsive toolkit; one codebase for desktop + mobile.
- **Cons**: **full UI rewrite**; must **re-solve** native audio and Whisper outside the
  Python ecosystem; discards the React/FastAPI investment; learning curve (Dart). The
  **most expensive** option.
- **Effort**: **very high** (dozens of PD just to reach Meetings parity).

### Option C — Consolidate on the **existing React web UI** + local daemon (recommended)
- **Idea**: the responsive UI **already exists** in React. The only blocker is
  audio/Whisper in the browser. Solution: keep the Python app as a **local daemon**
  (capture + Whisper + AI layer) exposing **API + WebSocket**; React consumes it and
  renders the responsive UI (including Meetings, with live transcription over WS).
- **Pros**: reuses **all** the React + FastAPI + AI-layer investment; real
  responsiveness (CSS/flex/grid, media queries); the heavy logic (audio, AI) stays
  where it already works (Python).
- **Cons**: needs **streaming** (WebSocket) of live transcription/state; the screen
  watcher and capture stay native (in the daemon); packaging as a desktop app (see
  Option D) for a native window + global shortcut + tray.
- **Effort**: **medium** (mostly wiring React screens to existing/easy-to-expose
  endpoints/WS).

### Option D — Wrap the web UI in a lightweight desktop shell
- **How**: **pywebview** (pure Python, fits the current backend), **Tauri** (Rust,
  small binary), or **Electron** (heavier) to give the Option C web UI a native window,
  global shortcut, and tray.
- **Pros**: a "real app" experience reusing the web UI; gradual migration (one screen
  at a time moves from Qt to web).
- **Cons**: one more packaging dependency; daemon↔shell IPC.
- **Effort**: **low-medium** for the skeleton (pywebview is fastest given the Python stack).

## 5. Recommendation

1. **Now (done/continue)** — Option **A**: finish Qt-screen responsiveness reusing
   `FlowLayout` + breakpoints. Immediate value, no risk.
2. **Strategic direction** — Option **C + D**, **not** Flutter: move the UI to the
   **React web UI that already exists**, with the Python app as a **local daemon** for
   capture + Whisper + AI, wrapped in a lightweight shell (**pywebview** as first
   choice). Rationale: Flutter would force **rewriting the UI and re-solving native
   audio** outside Python; the web route **reuses** React + FastAPI + the AI layer and
   gives real responsiveness for free. The native-audio constraint stays in Python in
   both paths — so the web path is strictly cheaper.

## 6. Suggested roadmap (phased, effort in PD)

- **Phase 0 — Qt responsiveness (short term)**: apply `FlowLayout`/breakpoints to the
  remaining screens. ~1 PD/screen.
- **Phase 1 — Live streaming in the API**: expose a WebSocket for live
  transcription/state (today desktop-only). ~3–5 PD.
- **Phase 2 — Meetings in the web UI**: rebuild the Meetings screen in React consuming
  the WS + endpoints (preparation, context, workspace/project, Q&A). ~5–8 PD.
- **Phase 3 — Desktop shell (pywebview)**: native window + global shortcut + tray;
  headless capture/Whisper daemon. ~3–5 PD.
- **Phase 4 — Parity and gradual migration**: move the remaining Qt screens to web,
  retiring the Qt GUI once at parity. Effort depends on scope.

## 7. Risks and decision points

- **Native audio**: in every option, capture stays in the Python daemon
  (parec/PulseAudio; later a PipeWire portal for Wayland). A browser cannot capture
  system audio without a native helper.
- **Packaging**: choose between pywebview (Python, simpler) and Tauri (smaller binary,
  more robust) — a Phase 3 decision.
- **Cost of maintaining two fronts** during the transition (Qt + web): mitigated by
  migrating **one screen at a time** and keeping the API as the single source of truth.

## 8. Decision (made)

- [x] **Approved direction: web (C+D)** — reuse the existing React web UI + a Python
  daemon for capture/Whisper/AI (over WebSocket) wrapped in a desktop shell.
- [x] Shell chosen: **pywebview** (pure Python, fits the current backend).

### Execution

- **E1 — pywebview shell** (Phase 3 first, lowest risk): wrap the React web UI already
  served by the API in a native window (`maestro_local/desktop_shell.py`), with a
  fallback to the current Qt GUI. Proves the web route without touching meetings.
- **E2 — Live streaming (Phase 1)**: move capture + Whisper + live state into a service
  in the API process and expose it over WebSocket.
- **E3 — Meetings in the web UI (Phase 2)**: rebuild the screen in React consuming E2.
- **E4 — Parity and gradual Qt retirement (Phase 4)**.
