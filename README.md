# Tasks Skill

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) plugin for structured task management with a full lifecycle.

Manage your project backlog entirely through Claude Code — add tasks, spec them interactively, plan implementations, track progress through review, and complete them with full change tracking.

## Features

- **Full task lifecycle**: inbox → speccing → planning → plan-review → implementing → reviewing → complete
- **Interactive speccing**: Claude guides you through defining Description, Motivation, Scope, Constraints, Changes, and Acceptance Criteria
- **Execution planning**: Automatically generates step-by-step implementation plans from your spec
- **Git worktree isolation**: Each task gets its own worktree and feature branch — main stays clean
- **Epics**: Group related tasks under a parent epic with automatic child tracking
- **Change tracking**: Auto-generated `revw.md` with file-level diff summaries
- **Backlog auditing**: Detect structural issues, stale tasks, and dependency problems
- **VS Code viewer**: Optional sidebar extension to browse your `.tasks/` backlog visually

## Install

```bash
claude plugin add LiorCohen/tasks-skill
```

This installs the `/tasks` skill into your Claude Code environment.

## Setup

After installing the plugin, just run `/tasks add <description>` in your project. Claude will create the `.tasks/` directory structure automatically on first use.

Add `.worktrees/` and `.temp/` to your project's `.gitignore`:

```
.worktrees/
.temp/
```

## Usage

All commands are accessed through `/tasks`:

### Basic Commands

| Command | Description |
|---------|-------------|
| `/tasks` | View the full backlog |
| `/tasks <id>` | View a specific task |
| `/tasks add <description>` | Add a new task to inbox |
| `/tasks add epic <description>` | Add a new epic |
| `/tasks prioritize <id> <high\|medium\|low>` | Set task priority |

### Lifecycle Commands

| Command | Description |
|---------|-------------|
| `/tasks spec <id>` | Start speccing — interactive Q&A to define the task |
| `/tasks plan <id>` | Create an execution plan from the spec |
| `/tasks plan-review <id>` | Mark plan as ready for review |
| `/tasks implement <id>` | Create branch + worktree, start coding |
| `/tasks review <id>` | Generate change report, submit for review |
| `/tasks complete <id>` | Merge branch, clean up worktree, mark done |

### Other Commands

| Command | Description |
|---------|-------------|
| `/tasks reject <id> [reason]` | Reject a task |
| `/tasks consolidate <id> into <target-id>` | Merge a task into another |
| `/tasks add-to-epic <epic-id> <description>` | Add a child task to an epic |
| `/tasks audit` | Run a full backlog health check |
| `/tasks install-viewer` | Install the VS Code sidebar viewer |
| `/tasks uninstall-viewer` | Remove the VS Code sidebar viewer |

## Task Lifecycle

```
    inbox
      ↓
   speccing      ← Interactive spec refinement
      ↓
   planning      ← Execution plan creation
      ↓
  plan-review    ← Review checkpoint
      ↓
 implementing    ← Code in isolated worktree
      ↓
   reviewing     ← Change report + review
      ↓
   complete      ← Merge, clean up, done

Any status → rejected
Any status → consolidated (into another task)
```

Each transition is committed automatically with a `Tasks:` prefix.

## Directory Structure

```
.tasks/
├── INDEX.md              # Backlog index
└── items/                # All task folders
    ├── 0-inbox/          # New tasks
    ├── 1-speccing/       # Being specified
    ├── 2-planning/       # Plan being written
    ├── 3-plan-review/    # Plan review checkpoint
    ├── 4-implementing/   # In progress
    ├── 5-reviewing/      # Ready for review
    ├── 6-complete/       # Done
    ├── 7-rejected/       # Rejected
    └── 8-consolidated/   # Merged into other tasks
```

Each task is a numbered folder (e.g., `items/0-inbox/42/`) containing:
- `task.yaml` — Pure YAML metadata (always present)
- `spec.md` — Specification with YAML frontmatter (created on add, filled during speccing)
- `plan.md` — Execution plan (created during planning)
- `impl.md` — Implementation report with iteration history (created during implementation)
- `revw.md` — Review notes and change summary (created during review)

## VS Code Viewer

The plugin includes an optional VS Code extension that adds a sidebar panel for browsing your `.tasks/` backlog:

```
/tasks install-viewer
```

This builds and installs a local `.vsix` extension. Reload VS Code after installing.

## Tips

- **Let speccing breathe.** The spec phase is where all decisions happen — Claude will challenge vague specs and suggest breaking large tasks into epics.
- **Don't skip phases.** The lifecycle is sequential. Claude will prompt you if you try to skip ahead.
- **One task at a time.** During implementation, the feature branch only touches its associated task.
- **Audit regularly.** `/tasks audit` catches structural issues, stale tasks, and broken dependencies.

## License

[AGPL-3.0](LICENSE)
