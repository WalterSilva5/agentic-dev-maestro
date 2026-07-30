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
- **E1 + E2 — Lazy imports + screens on demand**: the 9 rarely-opened
  "Ferramentas" hub screens (vault, library, apitester, kb, memory, english,
  translate, skills, guide) became **factories**
  (`MainWindow._lazy_factory`) instead of instances — imported/built only on
  first `_open_key`. None had external references in `main_window.py`, so
  deferring was safe (confirmed by grep and an offscreen test: the stack holds
  9 widgets at boot, grows by 1 per newly opened screen, no duplication on
  reopen). **Measured**: boot RSS dropped from ~174.2 MB to ~160.2 MB (**~14 MB,
  ~8%**), stable across 3 runs — method under `medir_rss()` below.
- **E3 — Model-size guidance**: Settings now shows the approximate RAM of the
  selected Whisper model (`WHISPER_MODEL_RAM_MB`), updating live — from ~75 MB
  (tiny) to ~3 GB (large-v3). Helps pick consciously.
- **E4 — Finding**: the `webmain` route (API + web UI, no GUI) **already loads
  no Qt** — confirmed (`grep PySide6` empty in `api/`, `webmain.py`). The
  headless daemon for the rest of the app already exists; only **Meetings**
  is missing, whose workers use `QThread`
  (`transcricoes/agent_service.py`, `live_assistant.py`, `transcriber.py`) —
  depends on the live WebSocket (E2/E3 of [Plan 11](migracao-toolkit-ui.md)),
  not solved here.
- **E5 — Finding**: no other heavy local model cache besides Whisper. The
  knowledge-base embeddings (`memory.py`) go through an HTTP API
  (OpenAI-compat), no local resident model to free.

## 3. To do (by effort)

- **E4 (remainder) — Meetings without QThread** (~2–3 PD, within Plan 11's
  W1/W2): move capture/transcription/live state to run without depending on
  Qt's event loop, enabling Meetings in the headless `webmain` daemon.

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

Method used for E1+E2 (repeatable): build `MainWindow` offscreen
(`QT_QPA_PLATFORM=offscreen`) in a fresh process, with an isolated temp DB, and
read `resource.getrusage(RUSAGE_SELF).ru_maxrss` right after `processEvents()`.
Run 3× to check stability.

> **Isolation caveat**: `SettingsView`/`_save_settings` writes to
> `~/.maestro-local/config.json` — a **real user file**, outside the temp SQLite
> DB. A manual verification script during this plan's development interacted
> with the Whisper model combo and **overwrote that real setting** (caught via
> the file's mtime, restored to the `small` default). The `temp_db` fixture in
> `tests/conftest.py` now isolates `config.json` too (`monkeypatch` on
> `config._CONFIG_FILE`); ad-hoc verification scripts (outside pytest) should do
> the same before simulating UI interaction that saves settings.
