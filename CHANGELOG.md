# Changelog

All notable changes to Sifty. The format loosely follows
[Keep a Changelog](https://keepachangelog.com); versions before the first
public release were development milestones.

## [0.5.0] — 2026-06

### Added

- **Checkup** — a read-only full-suite health scan (`sifty checkup` and a
  Home-screen hero button): junk, pending updates, registry orphans, stale
  downloads, low disk space, and startup bloat in one report, each finding
  with a one-tap action.
- **AI follow-up actions** — when an AI tool scan finds something, the result
  card offers a button that jumps to the screen that can act on it.
- **Self-update** (`sifty selfupdate`) via PyPI + pipx.
- **Git worktree cleanup** — detect and prune orphaned AI-agent worktrees
  (`Worktrees` mode in Smart cleanup).
- **VHD compaction** — compact WSL2/Hyper-V virtual disks via DISM.
- Installer intelligence: the Downloads-installers junk category only flags
  installers whose app is already installed.

### Changed

- TUI navigation consolidated into tabbed groups: **Clean** (Junk, Purge,
  Optimize, Smart) and **Apps** (Installed, Updates, Startup, Services); every
  former screen stays reachable via the command palette.
- Home redesigned: clickable stat cards, summaries cached between visits,
  compact admin status line.
- Browse… folder picker on the Purge and Smart cleanup screens.

### Fixed

- Worktree pruning honors the row selection and no longer crashes when an
  orphan directory exists on disk.
- Registry orphan scanner filters SystemComponent and winget-managed entries.

## [0.4.0] — 2026

- NTFS-aware duplicate detection (hardlinks counted once), concurrent junk
  scanning and hashing, registry orphan detection (read-only), apps-screen
  orphan panel.

## [0.3.0] — 2026

- Dev artifact purge (node_modules, dist, __pycache__, …), system optimize
  (DNS flush, thumbnail/prefetch/update-cache rebuild, DISM component
  cleanup), five new junk categories.

## [0.2.0] — 2026

- Layered architecture (core / windows / infra / cli / tui), smart cleanup
  (duplicates, large files, stale downloads), startup manager (reversible),
  curated services manager, cleanup profiles + Task Scheduler integration,
  low-disk watch with toast alerts, clean history (SQLite) + undo, `--json`
  scripting output, agentic AI with autonomy levels, live system monitor,
  on-demand UAC elevation, command palette, crash logging.

## [0.1.0] — 2026

- Initial release: junk scan/clean, disk analysis, duplicate finder, app
  list/uninstall (winget), updates via winget, file organization, local-AI
  advisor (Ollama), safety layer (Recycle Bin only, dry-run default,
  protected paths, audit log), Textual TUI.
