> 🇧🇷 [Versão em português](PLANO_ASSISTENTE_REUNIAO.ptbr.md)

# Plan — Real-Time Meeting Assistant

Evolution of the **Transcriptions** module (`maestro_local/transcricoes/`) from "record → stop →
transcribe → summarize" to **live tracking** during the meeting, with a direct
bridge to the board. Effort in man-days (md); staffing/schedule is left to the
leadership's discretion.

---

## 1. Objective

During a meeting/study, the app:
- Transcribes **continuously** (live transcription panel);
- Extracts actions, decisions, and open questions **incrementally**;
- Allows **asking the meeting** ("what did we decide about X?");
- At the end, turns the **actions into tasks** on the board with 1 click.

Differentiator: everything local (audio + Whisper) + AI with the already configured provider
(LM Studio/opencode/etc.), without sending audio to the cloud.

---

## 2. Experience (UX)

Layout of the Transcriptions screen in "live" mode (3 columns):
- **Left**: controls + history (as today).
- **Center**: live transcription scrolling, with block marking by pause (VAD).
- **Right**: dynamic panel with **Actions · Decisions · Questions** tabs, updated at
  each block. **"Ask the meeting"** box at the bottom.

When stopping: structured summary (as today) + **"Create tasks from actions"** and
**"Save to My Day"** buttons.

---

## 3. Architecture (how it fits into the current code)

| Layer | Where | What changes |
|---|---|---|
| Capture | `transcricoes/audio.py` | Already continuous (`parec`). Expose a rolling buffer (ring buffer) consumable without stopping the recording. |
| Transcription | `transcricoes/transcriber.py` | New `LiveTranscriber` (QThread) that at each window takes the buffer, applies VAD, and transcribes only the new segment; emits `partial_text`. |
| Live AI | `transcricoes/live_assistant.py` (new) | Debounce: every N seconds or M new words, sends the accumulated transcript to the provider and does **incremental extraction** (merge with what has already been extracted). Reuses `ai/providers.build_chat_model`. |
| Ask the meeting | same module | One-off call with the transcript as context. |
| Actions → tasks | `api/app.py` + view | Endpoint/path to create tasks from the actions (uses the existing `POST /api/tasks`). |
| UI | `gui/views/transcricoes_view.py` | Live mode (3 columns), reactive panels, threads that don't block the GUI. |

Principles: keep everything in **QThreads** (transcription and AI never on the GUI thread);
**degrade gracefully** (if there is no AI provider, only the live transcription runs).

---

## 4. Phases and tasks

> Status: Phases 1–4 **implemented** (verified in an offscreen smoke test). Missing an
> end-to-end run with real audio on a machine with a microphone.

### Phase 1 — Live transcription (~2–3 md) ✅
- [x] Rolling buffer in `audio.py` (`snapshot_audio()` reads without stopping the recording; mixing refactored into `_mix`).
- [x] `LiveTranscriber` (QThread): sliding window (10s) + VAD, emits `partial`.
- [x] Live transcription panel on the screen, with autoscroll.
- [x] Window/model constants (`LIVE_*`); live mode uses `base` by default.

### Phase 2 — Live incremental extraction (~2 md) ✅
- [x] `live_assistant.py`: `LiveExtractWorker` with incremental extraction (receives "already extracted" + "new segment", returns the merge; limited context).
- [x] Reactive Actions/Decisions/Questions panel (tabs with counters).
- [x] "Ask the meeting" (`LiveAskWorker`, one-off answer with transcript context).
- [x] Debounce by time (`LIVE_AI_MIN_SECONDS`) OR new words (`LIVE_AI_MIN_WORDS`), 1 extraction at a time.

### Phase 3 — Meeting → board bridge (~1 md) ✅
- [x] "Create tasks from actions" button: each action becomes a task (type CHORE, `requires_human=True`), in the chosen project.
- [x] Fallback: uses the live assistant's actions or, if there are none, the final AI summary's.

### Phase 4 — Polish (~1 md) ✅
- [x] State indicators (transcribing / no AI / thinking).
- [x] Long meeting: context sent to the AI limited (`_clamp_transcript`).
- [x] "Live assistant" toggle; the panel only appears during live recording.
- [ ] Final screenshot with real audio (pending — needs a machine with a microphone).

**Estimated total: ~6–7 md.** Phases 1→2→3 already deliver end-to-end value; phase 3 alone (without real time) is the best cost/benefit if you want to start light.

---

## 5. Technical tips

- **Windowing with overlap**: transcribe windows with ~1s of overlap and
  dedupe the repeated text at the edges — avoids cutting words between blocks.
- **VAD to cut at pauses**: faster-whisper already has `vad_filter=True`; use the
  pauses to close "stable" blocks (don't reprocess an already confirmed segment).
- **Model per mode**: `small` for the final summary (accuracy), `base`/`tiny` for the
  live one (latency). Keep it configurable in Settings → Transcriptions.
- **C.UTF-8 locale in the worker**: keep the already applied fix (Qt resets the LC_CTYPE and
  PyAV breaks) — applies to any new audio worker.
- **AI debounce**: don't call the provider at every word; trigger every ~15s or
  ~40 new words. Cancel the previous call if a new block arrives.
- **Limited context**: in a long meeting, send only the "recent window + accumulated
  summary" so as not to blow the provider's context/cost.
- **Everything in QThread**: transcription and AI outside the GUI thread; communicate via signals.
- **Graceful failure**: no AI provider → only live transcription; no `parec` →
  clear warning (the pattern already exists in the code).

## 6. UX tips

- Show the **state** clearly (chip "AI thinking…", "transcribing…").
- Extracted actions/decisions should be **editable** before becoming a task (the AI makes mistakes).
- One click to **discard** a suggested action.
- Shortcut to pause only the **AI extraction** (saves resources) while keeping the transcription.

---

## 7. Complementary features (roadmap that makes sense)

Items that connect with the rest of the app and enhance the meeting assistant:

- **Actions → tasks bridge** (~1–2 md) — already included in Phase 3; worth it as an
  independent feature even without real time.
- **Proactive assistant digest** (~3 md) — automatic summary (morning/end of day)
  with priorities, overdue, and stalled items; show it in the Dashboard. Reuses the logic of the
  `maestro-daily-report` skill.
- **Real global search** (~2 md) — today Ctrl+K only finds tasks; expand to
  notes, **transcriptions**, and comments via SQLite FTS.
- **Agenda/calendar by deadline** (~2 md) — calendar view of tasks by
  `due_date` (today only a list of overdue ones).
- **Recurring tasks / subtask templates** (~2 md).
- **Pomodoro linked to the task** (~1 md) — log time spent per task and feed
  the real cycle time in Metrics.
- **Real-time web** (~2 md) — WebSocket so that board/dashboard update when an
  agent makes changes via the API (today it needs a reload).
- **"Who spoke" diarization** (~4 md, heavier) — `pyannote` + model; greatly improves
  the meeting minutes, but it is the most costly item and the only one that pulls in a large dependency.

---

## 8. Risks and mitigation

| Risk | Mitigation |
|---|---|
| Whisper latency on CPU | Smaller model in the live mode; configurable window; state indicator. |
| AI provider latency/cost | Debounce + limited context; incremental extraction (doesn't reprocess everything). |
| Long meeting blows the context | Summarize the middle; send only the recent window + summary. |
| AI gets actions/decisions wrong | Editable panel + discard before it becomes a task. |
| GUI freezing | All processing in QThread; communication via signals. |

## 9. Acceptance criteria

- Transcription appears live with acceptable delay (a few seconds).
- Actions/decisions/questions update during the meeting without freezing the GUI.
- "Ask the meeting" answers based on what has already been said.
- When stopping, "Create tasks from actions" generates the correct tasks on the board.
- Without an AI provider, the live transcription keeps working.
