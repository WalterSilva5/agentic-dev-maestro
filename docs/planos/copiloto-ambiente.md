# 14 — Ambient copilot: Meetings as the product's core

> Goal: turn Meetings from "one screen among others" into the **core of the
> app**, and grow it from a meeting assistant into a **programmer's copilot** —
> contextual help while you work, not only while you talk. Product reference:
> [Cluely](https://cluely.com/).
>
> Tasks, subtasks and roadmap; effort in **person-days (PD)**. Allocation and
> scheduling are a leadership call.

## 1. What the reference does (taken from the site, not from memory)

| Pillar | How Cluely works |
|---|---|
| **No bot in the meeting** | Captures machine audio; never joins as a participant |
| **Floating overlay** | Local window above the rest, moveable, invisible in screen share |
| **Instant question** | Shortcut (Cmd/Ctrl+Enter) answers using the meeting **and what's on screen** |
| **Live transcription** | ~300 ms response, 12+ languages |
| **Real-time notes** | Formatted, shareable summary |

## 2. What Maestro already has (measured in the code)

Much of the foundation **already exists** — the pivot is less "build from
scratch" and more "lift it out of the Meetings screen and cut latency".

| Piece | State | File |
|---|---|---|
| System audio capture (no bot) | ✅ works | `transcricoes/audio.py` (267 l.) |
| Local transcription (Whisper) | ✅ works | `transcricoes/transcriber.py` (209 l.) |
| Live copilot (plan/actions/decisions/questions) | ✅ works | `transcricoes/live_assistant.py` (218 l.) |
| Ask with context | ✅ works | `agent_service.ask()` |
| Global shortcut | ⚠️ partial | `transcricoes/hotkeys.py` (34 l.) |
| Proactive tips | ✅ works | `coach.py` (141 l.) |
| History + search | ✅ works | `transcricoes/repository.py` |
| **See the screen** | ❌ **broken** | see section 3 |

## 3. Finding that reshapes the plan: seeing the screen does not work

The "screen watcher" exists in the UI but **captures nothing on this machine**.
Verified:

```
Qt platform: wayland
null pixmap? True | size: 0 x 0     ← screen.grabWindow(0)
```

`QScreen.grabWindow()` does not work on **native Wayland** — it is an X11-era
API. The session here is Wayland (`XDG_SESSION_TYPE=wayland`), so the feature has
always been dead in this environment, failing silently.

The correct path on Wayland is the **XDG Desktop Portal (ScreenCast) + PipeWire**,
which is available on the machine (`kde.portal`, `gtk.portal` present). It also
brings explicit system-level consent (the compositor asks what to share) instead
of silent capture.

**Consequence:** "see the screen" is a prerequisite for the programming copilot
and must be rebuilt, not tweaked. It is the single largest task in this plan.

## 4. Gap between today and the target

| Dimension | Today | Target |
|---|---|---|
| **Where it lives** | Inside the main window, one tab | Always-reachable floating overlay |
| **When it helps** | Only during a recording "meeting" | Ambient: while you work |
| **Speech latency** | 10 s windows (`LIVE_WINDOW_SECONDS`) | Short segments, ~1–2 s |
| **Item latency** | 15 s or 40 words, 45 s timeout | On-demand question answers now |
| **See the screen** | Broken on Wayland | Portal + PipeWire, with consent |
| **History** | A list inside Meetings | First-class surface, global search |

## 5. Phases, tasks and subtasks

### F1 — Actually see the screen (~4–6 PD) — **unblocks the rest**

- [ ] **F1.1 — Capture via portal** (~3–4 PD)
  - · XDG Portal `ScreenCast` + PipeWire; persistent session (permission asked
    once, not per frame)
  - · Fall back to `grabWindow` on X11 sessions (still works there)
  - · Detect and **warn** when no capture is available — today it fails silently
- [ ] **F1.2 — Frame on demand** (~1 PD)
  - · One frame at question time instead of periodic capture: less vision cost
    and less sensitive data in flight
- [ ] **F1.3 — Privacy controls** (~1 PD)
  - · Visible indicator while the screen is being read; one-click off
  - · Pick monitor/window; remember the choice

### F2 — Copilot overlay (~5–7 PD)

- [ ] **F2.1 — Floating window** (~2–3 PD)
  - · Always on top, moveable, compact; toggled by shortcut
  - · **Wayland constraint**: clients cannot portably control position or
    always-on-top. Evaluate `layer-shell` (KDE/wlroots) and document behaviour
    per compositor — do not promise what the protocol does not provide
- [ ] **F2.2 — Instant question** (~2 PD)
  - · Global shortcut opens the overlay with the cursor already in the field
  - · Answers with available context: recent transcript + screen frame
  - · Streamed answer (token by token, not waiting for the end)
- [ ] **F2.3 — Proactive suggestions** (~1–2 PD)
  - · Reuse `coach.py`, but triggered by **context events** (an error on screen,
    a question asked on the call), not only by time

### F3 — Latency (~3–5 PD)

- [ ] **F3.1 — Short segments with VAD** (~2–3 PD)
  - · Voice activity detection to cut on pauses instead of fixed 10 s windows
  - · Smaller model on the live path; the good model stays for the final text
- [ ] **F3.2 — On-demand answers take priority** (~1 PD)
  - · A user question jumps ahead of periodic extraction instead of waiting for
    a free worker
- [ ] **F3.3 — Measure** (~1 PD)
  - · Record speech→text and question→answer latency; without numbers there is
    no way to claim improvement

### F4 — Ambient mode, beyond meetings (~4–6 PD)

- [ ] **F4.1 — Work session** (~2–3 PD)
  - · Separate "session" from "meeting": recording audio becomes optional; a
    session can be just screen + questions
  - · `MeetingSession` already separates inputs from outputs — extend, don't
    rewrite
- [ ] **F4.2 — Code context** (~2–3 PD)
  - · Read what's on the editor screen and answer about the visible code
  - · Link to board tasks when the user authorizes (already opt-in)

### F5 — History as the primary surface (~3–4 PD)

- [ ] **F5.1 — Global search** (~2 PD)
  - · Search transcripts, answers and items; dedicated shortcut
- [ ] **F5.2 — Timeline** (~1–2 PD)
  - · Sessions and meetings on one timeline, filterable by project/period

### F6 — Reposition in navigation (~1 PD)

- [ ] **F6.1** — Meetings/Copilot at the top of the WORK group, with history
  reachable straight from the menu

**Estimated total: ~20–29 PD.**

## 6. Roadmap

```
F1 See screen ──► F2 Overlay ──► F4 Ambient mode ──► F5 History ──► F6 Nav
  (4–6 PD)        (5–7 PD)       (4–6 PD)            (3–4 PD)       (1 PD)
       └──────► F3 Latency (3–5 PD) ─────┘
```

F1 unblocks F2 and F4 (without seeing the screen there is no programming
copilot). F3 runs in parallel from F2 onward.

## 7. Risks and constraints

| Risk | Impact | Note |
|---|---|---|
| **Wayland limits overlays** | High | Position and always-on-top are not portable; depends on the compositor's `layer-shell` |
| **Portal requires consent** | Medium | A quality, not a defect — but it changes UX (one permission per session) |
| **Global shortcut on Wayland** | Medium | `pynput` starts, but captures events via X11/XWayland; keys in native Wayland apps may not arrive |
| **300 ms latency** | Medium | Cluely uses a cloud service; with local Whisper a realistic target is 1–2 s, not 300 ms. **Do not promise parity** |
| **AI cost** | Medium | An ambient copilot calls the model far more often than a one-off meeting |

## 8. Open decision: how far to copy the reference

Cluely positions itself explicitly as **undetectable** — absent from the
participant list and from screen shares, with marketing that suggests use in
interviews and negotiations.

Two things are worth separating:

- **A local overlay that doesn't pollute your screen share**: useful and
  unproblematic — they're your notes, nobody else needs to see them.
- **Deliberately hiding from the other party that an AI is assisting**: that is
  a product choice with consent implications, and in many jurisdictions
  recording other people's audio requires notice.

This plan builds the **copilot**; "undetectability" as a product goal stays an
explicit decision by the project owner, not something inherited from the
reference.

- [ ] Build the copilot only (recommended)
- [ ] Also pursue undetectability
