# Sifty — Interactive TUI Design (plan, not yet built)

A design for a full-screen, interactive terminal app for Sifty using
**[Textual]**. This is a planning document — nothing here is implemented yet.
See [ARCHITECTURE.md](ARCHITECTURE.md) for the underlying engine.

## Goal

Turn Sifty from a command-per-action CLI into a navigable app you *live in*:
arrow-key/mouse navigation, a start menu, checkbox selection of what to delete,
live-updating tables, and a conversational AI panel — while keeping every
existing `sifty <command>` intact for scripting.

## Principles

1. **The TUI is a frontend, not a rewrite.** It calls the same core functions
   (`junk.scan`, `disk.find_duplicates`, `apps.installed_apps`, …). No business
   logic lives in the TUI layer.
2. **Safety is unchanged.** Destructive actions still go through `safety.trash()`,
   still preview, still confirm (now via a modal), still refuse protected paths.
   The TUI cannot bypass the guardrails.
3. **Never freeze the UI.** Every scan/hash/winget call is blocking and slow, so
   it runs in a Textual worker (background thread); the UI shows progress and
   stays responsive.

## Why Textual

- Same author/stack as **Rich**, which we already use — our `human_size()` and
  Rich tables drop straight into Textual widgets.
- First-class widgets for exactly what we need: `DataTable`, `SelectionList`
  (checkboxes), `Input`, `Tree`, `ProgressBar`, `Tabs`, modal screens, and a
  built-in command palette.
- Cross-platform; renders best in **Windows Terminal** (recommend it over legacy
  conhost). Mouse + keyboard both supported.
- Has a test harness (`App.run_test()` + `Pilot`) to simulate keypresses in CI.

## Recommended prerequisite: the `sifty_core` seam

The TUI is the second frontend, so this is the natural moment to do the
extraction discussed earlier: move the pure logic (no Typer) into `sifty_core`,
leaving `sifty_cli` and `sifty_tui` as thin layers. Not strictly required
(core functions are already importable), but it keeps both frontends honest and
makes packaging cleaner. Decide at build time.

## App structure

```text
src/sifty/tui/
├── app.py            # SiftyApp(App): screens, global bindings, theme
├── screens/
│   ├── home.py       # dashboard: volume gauges + quick actions
│   ├── junk.py       # SelectionList of categories → preview → confirm modal
│   ├── disk.py       # volumes table + biggest-items tree + duplicates
│   ├── apps.py       # DataTable of installed apps; startup list
│   ├── updates.py    # DataTable of winget upgrades; apply selected
│   └── ai.py         # chat log + input; streams from Ollama
├── widgets/
│   ├── confirm_modal.py   # reusable "X items, Y GB → Recycle Bin?" modal
│   └── busy.py            # progress/spinner overlay for workers
└── workers.py        # thin async wrappers that run core fns in threads
```

Launched via a new `sifty tui` command (added to `cli.py`); optionally make a
bare `sifty` (no args) launch the TUI instead of printing help.

## Layout & navigation

- **Left sidebar** (`ListView`): Home · Junk · Disk · Apps · Updates · AI.
  Arrow keys move; Enter/click opens that screen in the content pane.
- **Content pane**: the active screen.
- **Footer**: context bindings (e.g. `space` select · `a` apply · `r` refresh ·
  `?` help · `q` quit) + the Textual command palette (`ctrl+p`).
- **Header**: title + admin/winget/Ollama status dots (from `doctor`).

## Screen behaviours

| Screen | Widgets | Actions |
|---|---|---|
| Home | volume `ProgressBar`s, total reclaimable junk, update count | jump to any screen |
| Junk | `SelectionList` of categories with sizes | space to toggle, `a` → confirm modal → `trash(apply)`; live size refresh |
| Disk | `DataTable` (volumes) + `Tree` (biggest) + duplicates table | pick a path; run dedup in a worker with progress |
| Apps | `DataTable` (name/size/publisher), sortable | select → uninstall (confirm modal → winget) |
| Updates | `DataTable` of upgrades | check all / select → apply (confirm) |
| AI | scrollable `RichLog` + `Input` | type a question; stream tokens from Ollama; offer "use current screen's data as context" |

## Concurrency model

- Wrap each core call in a Textual `@work(thread=True)` worker (`workers.py`).
- Worker posts results back via a message; the screen updates its table/list.
- Show a `busy.py` overlay or `ProgressBar` while running; allow cancel where
  feasible (duplicate scan, winget check).
- AI chat uses Ollama streaming (`stream=True`) to append tokens live to the log.

## Safety integration (must-haves)

- Destructive actions open `confirm_modal.py` showing count + size + "→ Recycle
  Bin", defaulting to **No**.
- The modal calls the same `safety.trash(..., dry_run=False)` path; protected
  paths are still refused and surfaced as a non-blocking toast.
- A persistent dry-run/"safe mode" toggle in the header that, when on, makes every
  action a preview regardless of confirmation — good default for first launch.

## Packaging notes

- Add `textual` to runtime deps; keep `textual-dev` in the `dev` extra for the
  `textual run --dev` hot-reload + console.
- PyInstaller: Textual ships CSS/asset files — bundle with
  `--collect-all textual` (extend the `package-exe` skill when we get there).

## Testing

- Core logic stays covered by existing unit tests.
- TUI flows tested with `async with app.run_test() as pilot:` — simulate
  `pilot.press("down","enter","space","a")` and assert the confirm modal appears
  and that `trash` is called with `dry_run` per the safe-mode toggle (monkeypatch
  `send2trash`, as today).

## Milestones

1. **M1 — Skeleton:** `SiftyApp`, sidebar nav, Home screen with volume gauges,
   `sifty tui` entry point. Proves the frame + worker pattern.
2. **M2 — Junk screen:** SelectionList + confirm modal + safe-mode toggle. First
   real destructive flow end-to-end (the highest-value screen).
3. **M3 — Disk / Apps / Updates screens.**
4. **M4 — AI chat** with streaming.
5. **M5 — Polish:** theme, command palette actions, help screen, `--dev` reload.

## Risks / open questions

- **Terminal support:** recommend Windows Terminal; document degraded legacy
  conhost behaviour.
- **Long winget/dedup latency:** mitigated by workers + progress + cancel.
- **Bare `sifty` → TUI vs help?** Decide whether no-args launches the TUI
  (friendlier) or stays as help (scripting-safe). Leaning: launch TUI when run
  interactively (a TTY), print help when piped.
- **Core extraction first?** Recommended but optional; confirm before M1.

[Textual]: https://textual.textualize.io
