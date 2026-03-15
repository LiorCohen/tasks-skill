# Changelog

All notable changes to the tasks-skill plugin are documented here.

## [3.1.1] - 2026-03-15

### Fixed

- **README**: Updated stale v1 file structure (`task.md`/`changes.md`) to v2 (`task.yaml`/`spec.md`/`plan.md`/`impl.md`/`revw.md`).
- **SKILL.md / workflows.md contradiction**: Aligned skip-forward transition policy — allowed with `--force` after challenging the user.
- **SKILL.md / workflows.md**: Added missing YAML frontmatter to `impl.md` creation template (now matches `schemas.md`).
- **CLI transition validation**: Added `VALID_TRANSITIONS` map; `cmd_transition` now rejects invalid transitions unless `--force` is passed.
- **Cycle detection in `audit`**: Replaced broken shared-visited algorithm with correct 3-color DFS.
- **`cmd_review` branch name**: Now reads actual branch from worktree instead of guessing via `slugify`.
- **`.gitkeep` creation**: `ensure_status_dirs` now creates `.gitkeep` files so empty status directories are tracked by git.

### Viewer (1.1.1)

- **Removed priority buttons**: They bypassed the CLI pipeline (no INDEX.md rebuild or git commit). Priority is now read-only in the viewer; use `/tasks prioritize` instead.
- **Removed dead CSS**: `.repo-tag` and `.task-tags` classes left over from the removed `repos` field.
- **Distinct complete emoji**: Complete status now uses a different emoji from Plan Review.

---

## [3.1.0] - 2026-03-15

### Added

- **`/tasks migrate` command**: Detects projects using the pre-v3 layout (status dirs directly under `.tasks/`) and moves them into `.tasks/items/`, rebuilds INDEX.md, and commits. Always asks the user before migrating.
- **Legacy layout warnings**: `list` and `audit` commands now include a warning when legacy status directories are detected outside `items/`, prompting the user to run `/tasks migrate`.

---

## [3.0.0] - 2026-03-13

### Breaking Changes

- **`items/` subdirectory**: All task status directories (0-inbox, 1-speccing, etc.) now live under `.tasks/items/` instead of directly under `.tasks/`. INDEX.md stays at `.tasks/INDEX.md` with updated links. Existing `.tasks/` directories need their status folders moved into `items/`.

---

## [2.2.0] - 2026-03-12

### Added

- **`/tasks help` command**: Prints a complete command reference listing all available `/tasks` subcommands.
- **Viewer command discoverability**: Added `install-viewer` / `uninstall-viewer` to the workflows command reference table and SKILL.md quick reference.
- **`install-viewer` / `uninstall-viewer` CLI commands**: One-step build, install, and removal of the VS Code viewer extension with structured JSON output.
- **CONTRIBUTING.md**: Project structure, release checklist, testing instructions, and code style notes.
- **CLAUDE.md**: Release process reference for Claude Code.

### Fixed

- **Detail panel tracks task across status changes**: Panel now keys by task ID and scans status directories dynamically, so it stays connected when a task transitions (e.g., inbox → speccing).

### Viewer (1.1.0)

- Panel resolves task location on every refresh instead of caching the initial path.
- Webview state serializes `taskId` instead of `taskRelPath` (backward-compatible deserialization for old state).

## [2.0.0] - 2026-03-12

### Breaking Changes

- **5-file task structure**: Tasks now use separate files instead of a single `task.md`:
  - `task.yaml` — pure YAML metadata (no `---` delimiters)
  - `spec.md` — specification with YAML frontmatter
  - `plan.md` — execution plan with YAML frontmatter
  - `impl.md` — implementation report with iteration history and YAML frontmatter
  - `revw.md` — review notes (replaces `changes.md`) with YAML frontmatter
- **`repos` field removed**: All references to the `repos` metadata field have been removed from the CLI, schemas, and viewer.

### Added

- **Python CLI** (`scripts/tasks_cli.py`): Deterministic CLI for all mechanical task operations (add, transition, prioritize, list, review, complete, audit, reject, consolidate, epic-sync, sync-index). All output is structured JSON.
- **Implementation iteration model**: Tasks track multiple implementation iterations in `impl.md`, each with changes made, acceptance criteria results, and optional devil's advocate review.
- **Devil's advocate subagent**: After each implementation iteration, a fresh subagent with clean context can review the work assuming it's wrong, producing structured findings.
- **Critic subagent gates**: Every status transition requires a critic subagent review with a clean context window before proceeding.
- **Explicit user approval**: All state transitions require explicit user approval — no auto-transitions.
- **Epic support**: `add-epic`, `add-to-epic`, `epic-sync` commands with parent/child relationships and priority inheritance.
- **Structural audit**: `audit` command runs 5 categories of checks (structural integrity, metadata compliance, INDEX.md sync, spec heading consistency, dependency integrity).

### Changed

- **CLI modularized**: Monolithic `tasks_cli.py` (1550 lines) split into 12 focused modules under `tasks_lib/`.
- **Viewer updated**: Backlog view and task detail panel read `task.yaml` + `spec.md` (with legacy `task.md` fallback). Tabs now show spec/plan/impl/revw.
- **Schemas rewritten**: All templates updated for the 5-file structure with complete field documentation.
- **Workflows updated**: Implementation section expanded with iteration workflow, devil's advocate prompt, and transition protocol.

## [1.0.0] - 2026-03-11

### Added

- Initial release of the tasks skill plugin for Claude Code.
- Task lifecycle: inbox, speccing, planning, plan-review, implementing, reviewing, complete, rejected, consolidated.
- VS Code viewer extension with backlog sidebar and task detail panel.
- INDEX.md auto-generation with priority grouping.
- Skill prompts (SKILL.md, workflows.md, schemas.md) for Claude Code integration.
