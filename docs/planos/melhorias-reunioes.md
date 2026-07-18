# Plan — Component grouping and Meetings flow improvements

> Goal: reduce the coupling of the Meetings screen (currently a god object),
> group components into cohesive units, and optimize both the usage flow and
> resource consumption. Effort in **person-days (PD)**; staffing/schedule is a
> leadership decision.

## 1. Diagnosis (measured in the code, not impressions)

| Metric | Current value | Comment |
| --- | --- | --- |
| `gui/views/transcricoes_view.py` | **2221 lines** | ~65% of the whole meetings module (3386 lines) |
| Methods in the view | **103** | UI, AI orchestration, persistence and audio all in one place |
| State attributes (`self._*`) | **129** | Scattered state, no cohesive model |
| Widgets (`self.x`) | **56** | Many widgets driven by index/visibility |
| QThread worker types orchestrated by the view | **6** | Transcriber, LiveTranscriber, LiveExtract, LiveAsk, Analyze, Vision |
| References to the 2 transcript fields | **31** | `transcript_edit` (static) vs `live_transcript_edit` (live) |
| Duplicate keys in `i18n_catalog.py` | **17** | e.g. "Excluir", "Gravar", "Histórico", "Copiar" |

What the user feels: two transcript fields swapped by visibility, the "Live"
panel sitting outside the numbered steps (1 Prepare → 2 Record → **?** →
3 Result), and context being rebuilt on every extraction.

## 2. Improvement tracks

### A. Component grouping (biggest structural win)

- **A1 — Extract composite widgets from the view.** Move the already
  well-delimited blocks into `gui/meetings/` as their own widgets with clear
  signals: `DestinationBar` (workspace+project), `PreparationCard` (type,
  agenda, context), `RecordingCard` (collapsible audio, record, live),
  `LiveAssistantPanel` (live transcript + tabs + ask), `ResultCard`
  (transcript, summary, actions), `HistoryPanel` (search, list, context menu,
  empty state). The view becomes composition + orchestration. **~5 PD.**
- **A2 — Meeting state model.** Replace the ~129 loose attributes with a
  `MeetingSession` dataclass (`transcript`, `prep`, `context_items`,
  `live_state`, `rec_id`, `md_source`). One place to save/restore (today the
  autosave depends on several fields). **~2 PD.**
- **A3 — Persistence service.** Move SQLAlchemy queries out of the view into
  `transcricoes/repository.py` (`save_session`, `load_session`, `list_history`,
  `archive`, `delete`, `reorder`). **~1.5 PD.**
- **A4 — AI orchestrator.** Concentrate the 6 workers in a
  `MeetingAgentService` exposing `transcribe()`, `extract()`, `ask()`,
  `analyze()`, `see_screen()` and emitting signals; the view only reacts.
  **~2 PD.**

### B. Meetings flow (UX)

- **B1 — Unify the transcript.** A single field with a "live" indicator while
  recording, instead of two fields swapped by visibility (31 references
  today). Removes a whole class of "wrong field visible" bugs. **~1.5 PD.**
- **B2 — Fit the assistant into the flow.** The "Live" panel becomes the
  numbered step **3. Assistant** (Result becomes 4), or is embedded in step 2
  while recording — today it floats between steps. **~1 PD.**
- **B3 — Flow progress bar.** A top indicator showing where the meeting is
  (prepared → recording → transcribing → analyzed), highlighting the current
  state. **~1 PD.**
- **B4 — Contextual actions.** Enable/hide actions per state (e.g. "Create
  tasks" only when actions exist; "Export" only with content) instead of
  always-visible, sometimes-inert buttons. **~0.5 PD.**

### C. Resource optimization

- **C1 — Stream audio to disk.** Today the whole buffer stays in RAM
  (`_chunks.append`), ~230 MB/hour per stream, because the final WAV needs it.
  Write incrementally to the file and keep only the live window. **~2 PD.**
  *(The per-window repeated copy has already been fixed.)*
- **C2 — Cache the meeting context.** `_meeting_context()` is called from 5
  places, redoing queries on every extraction; cache it and invalidate by event
  (project switch, new attachment, preparation edit). **~0.5 PD.**
- **C3 — Truly incremental extraction.** Send only the transcript delta plus a
  digest of the state, instead of the whole state each cycle — cuts tokens and
  live latency. **~1 PD.**

### D. Hygiene

- **D1 — Deduplicate the i18n catalog.** 17 repeated keys (last one wins, so
  there are dead translations); consolidate and add a test that fails on
  duplicates. **~0.5 PD.**
- **D2 — Flow regression tests.** Cover what already broke before: opening from
  history switches meetings, manual answers preserved on re-analysis,
  autosave/restore of `live_state_json`, "New meeting" reset. **~1.5 PD.**

## 3. Suggested order

Each phase delivers value on its own and de-risks the next:

1. **Phase 1 — Safety net** (D2, D1) — **~2 PD.** Tests before touching structure.
2. **Phase 2 — Componentization** (A1, A2) — **~7 PD.** The bulk of the
   maintainability win; the view stops being a god object.
3. **Phase 3 — Layers** (A3, A4) — **~3.5 PD.** Persistence and AI out of the UI.
4. **Phase 4 — Flow** (B1, B2, B3, B4) — **~4 PD.** Much simpler after
   componentization.
5. **Phase 5 — Resources** (C1, C2, C3) — **~3.5 PD.**

**Estimated total: ~20 PD.**

## 4. Risks and mitigation

- **Refactoring without a net** — mitigated by Phase 1 (tests first) and by
  keeping public widget/handler names during extraction.
- **Visual regression** — validate each phase with offscreen renders of the
  screens (the same method already used for the documentation screenshots).
- **Scope creep** — phases are independent; you can stop after any of them
  without leaving the code half-done.

## 5. Pending decision

- [ ] Approve the plan and the phase order.
- [ ] Decide how far to go now (suggestion: Phases 1–2, ~9 PD, which already
      solve the god object and set the base for the rest).
