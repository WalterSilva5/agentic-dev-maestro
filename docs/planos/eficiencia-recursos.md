# 12 — Resource efficiency plan

> Goal: reduce the `local-client`'s memory and CPU use. This document separates
> the **real cause** from **perception** ("Python is heavy"), lists what is
> already done and what remains, with effort in **person-days (PD)**. Allocation
> and scheduling are a leadership call.

## 1. Diagnosis (measured in the code)

The "Python for everything" perception points at the wrong place. The weight is
not the glue language, but **what** runs and **how**:

1. **Whisper model resident forever** — `transcriber._cached_model` stays in
   memory after first use and was never freed. The default `small` int8 is
   hundreds of MB sitting idle when not transcribing. **The biggest RAM culprit.**
   The engine is C++ (ctranslate2), not Python — changing the UI language does not
   affect it.
2. **One fat process** — the Qt app runs **Qt + FastAPI + ML model + threads +
   global-hotkey listener** in a single process. This is **architecture, not
   language**: any front end (Flutter/Java/web) would add its runtime on top of
   that core, which stays in Python because of audio capture + Whisper.
3. **Idle 1s timer** — the main window mirrored recording state to the sidebar via
   an **always-on** 1s QTimer, waking the CPU even when idle.
4. **Eager screen instantiation** — the main window builds **all** views at boot,
   even unopened ones. A memory/startup-time cost.

## 2. Applied (done)

- **Free Whisper when idle** (`transcriber.release_model`): after ~4 min with no
  recording/transcription, the model is freed and RAM returns to the system
  (it reloads on next use). `agent_service.is_busy()` / `view.is_busy()` guards
  ensure it is never freed during use.
- **Event-driven recording widget**: the 1s poll is gone; the view emits
  `recording_state_changed` on start/stop and each second while recording. Zero
  idle timer for this.
- **Earlier gains** (past sessions): `snapshot_since` for live audio
  (constant-cost window; previously copied the whole buffer every 10s); Whisper
  `cpu_threads` capped at half the cores (previously saturated the CPU); coach
  without per-minute N+1 queries.

## 3. To do (by effort)

### Low risk
- **E1 — Lazy imports at boot** (~1 PD): defer heavy imports (uvicorn, rarely used
  view libs) to cut startup time and idle footprint. Measure before/after with
  `tracemalloc`/RSS.
- **E2 — Instantiate screens on demand** (~2–3 PD): build each view on first
  access (lazy) instead of all at boot; keep navigation and state. Cuts startup
  RAM — heavy screens (board, meetings) only cost when opened.
- **E3 — Model-size guidance** (~0.5 PD): document/expose the quality×RAM
  trade-off (`tiny`/`base`/`small`) in Settings; a conscious default.

### Medium (structural)
- **E4 — Headless daemon (web route)** (~2–3 PD): run capture + Whisper + API
  without the Qt GUI loaded. The biggest structural memory gain, coinciding with
  **W3** of [Plan 11](migracao-toolkit-ui.md): the light UI (web/shell) separated
  from the heavy daemon. Removes the Qt cost when only the back end is needed.
- **E5 — Idle resource unloading** (~1–2 PD): extend the Whisper pattern to other
  costly caches (e.g., knowledge-base models/embeddings), freeing them when
  unused.

## 4. Where efficiency is NOT

- **Changing the UI language** (Flutter/Java): does not shrink the heavy core
  (Whisper/audio stays native Python) and **adds** the new toolkit's runtime.
  Efficiency comes from **architecture** (split daemon/UI, free idle resources,
  gate timers), not from rewriting the interface.
- **Micro-optimizing glue Python**: the time/memory is in the ML and Qt, not in
  application loops.

## 5. Tracking metric

Before each item, record **idle RSS** (app open, not recording) and **peak RSS**
(during transcription), plus **boot time**. Compare after the change. Without a
measurement, there is no proven gain.
