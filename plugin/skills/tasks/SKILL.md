---
name: tasks
description: Manage tasks and plans using the .tasks/ directory.
---

# Task Management Skill

Manage the project backlog, track progress, and organize implementation plans.

---

## CLI Tool

Most mechanical operations (creating files, moving folders, updating frontmatter, rebuilding INDEX.md, git commits) are handled by the `tasks_cli.py` script. This eliminates manual file manipulation and ensures consistency.

**Resolve the CLI path** at the start of any `/tasks` command:

```bash
TASKS_CLI="${CLAUDE_SKILL_DIR}/scripts/tasks_cli.py"
```

**All CLI output is structured JSON** to stdout. Errors go to stderr. The envelope format:

```json
{"ok": true, "command": "add", "data": {"id": 1, ...}, "warnings": [...]}
{"ok": false, "command": "add", "error": "message"}
```

**Important:** Parse the JSON output to extract IDs, paths, and warnings. When `data.epic_sync_needed` is present, run `epic-sync` before committing. When `warnings` is present, review each warning and act if needed.

---

## Directory Structure

```
.tasks/
├── INDEX.md              # Index file - task numbers, titles, links
└── items/                # All task folders live here
    ├── 0-inbox/          # Open tasks (not yet started)
    ├── 1-speccing/       # Spec being refined (interactive solicitation)
    ├── 2-planning/       # Plan being created
    ├── 3-plan-review/    # Plan review checkpoint
    ├── 4-implementing/   # Currently being worked on
    ├── 5-reviewing/      # Implementation complete, under review
    ├── 6-complete/       # Done
    ├── 7-rejected/       # Rejected or irrelevant
    └── 8-consolidated/   # Consolidated into other tasks
```

**Note:** `.gitkeep` files ensure empty directories are tracked in git. Do not delete these files.

Each task is a folder named by its ID containing up to 5 files:
- `task.yaml` - metadata (pure YAML, always present)
- `spec.md` - specification (pure markdown, created on add, filled during speccing)
- `plan.md` - execution plan (created during planning phase)
- `impl.md` - implementation report with iteration history (created during implementation)
- `revw.md` - review notes and change summary (created during review)

**Note:** Priority (high/medium/low) is a field in `task.yaml`, not a directory. Tasks are organized by status in directories. In INDEX.md, priority sub-sections appear under the Inbox heading.

**Reference:** See [schemas.md](schemas.md) for full file schemas and templates.

---

## Commands

### Help

```
/tasks help
```

Print this command list:

```
/tasks                             — View backlog
/tasks list                        — View backlog (alias)
/tasks <id>                        — View single task
/tasks add <description>           — Add task to inbox
/tasks add epic <description>      — Add epic to inbox
/tasks add-to-epic <eid> <desc>    — Add child task to epic
/tasks prioritize <id> <level>     — Set priority (high/medium/low)
/tasks spec <id>                   — Start speccing
/tasks plan <id>                   — Start planning
/tasks plan-review <id>            — Mark plan ready for review
/tasks implement <id>              — Start implementing
/tasks review <id>                 — Submit for review
/tasks complete <id>               — Complete task (merge + cleanup)
/tasks reject <id> [reason]        — Reject task
/tasks consolidate <id> into <id>  — Consolidate into another task
/tasks audit                       — Run structural audit
/tasks migrate                     — Migrate legacy layout to items/
/tasks install-viewer              — Build & install VS Code extension
/tasks uninstall-viewer            — Remove VS Code extension
```

---

### View Backlog

```
/tasks
/tasks list
```

**Run:** `python3 $TASKS_CLI list`

Parse the JSON output and render a markdown table with columns: `Status`, `Priority`, `#`, `Type`, `Task`.

**Table format:**

```
| Status | Priority | # | Type | Task |
|--------|----------|---|------|------|
```

**Type column values:**
- `Epic` for epic tasks (type: epic)
- Blank for change tasks (default, omit for brevity)

**Epic children:** Tasks with `parent_epic` are displayed with their parent reference appended in the Task column: `Task title (← #175)`. This makes epic membership visible at a glance.

**Status column values:**
- `📝 Speccing`
- `📐 Planning`
- `✅ Plan Review`
- `🔨 Implementing`
- `🔍 Reviewing`
- `📥 Inbox` (for tasks in items/0-inbox/)

**Priority column values:**
- `🔴 High`
- `🟡 Med`
- `🔵 Low`
- `⚪ —` (unprioritized or null)

**Sort order:** Active statuses first (in the order listed above), then inbox tasks by priority (high, med, low, unprioritized). Within each group, sort by task ID descending.

End with a summary line:

```
**N open** — X high, Y med, Z low, W unprioritized
```

---

### View Single Task

```
/tasks 19
```

Read `items/<status-dir>/19/task.yaml` for metadata and `items/<status-dir>/19/spec.md` for the full specification.

---

### Add New Task

```
/tasks add <description>
/tasks add epic <description>
```

**Run:** `python3 $TASKS_CLI add <description>` or `python3 $TASKS_CLI add-epic <description>`

The CLI creates the task folder, writes `task.yaml` + `spec.md`, rebuilds INDEX.md, and commits. Parse the JSON output to get the new task ID from `data.id`.

---

### Add Task to Epic

```
/tasks add-to-epic <epic-id> <description>
```

**Run:** `python3 $TASKS_CLI add-to-epic <epic-id> <description>`

The CLI verifies the epic, creates the child task with `parent_epic` and `priority: inherit`, updates the epic's Children table, rebuilds INDEX.md, and commits. Parse `data.id` for the new task ID.

---

### Prioritize Task

```
/tasks prioritize <id> <high|medium|low>
```

**Run:** `python3 $TASKS_CLI prioritize <id> <level>`

The CLI updates `task.yaml`, rebuilds INDEX.md, and commits. Errors if the task inherits priority from an epic.

---

### Start Speccing

```
/tasks spec <id>
```

**Step 1 — Transition (CLI):**

**Run:** `python3 $TASKS_CLI transition <id> speccing`

The CLI moves the folder, updates `task.yaml` and INDEX.md. If `data.epic_sync_needed` is present, run `python3 $TASKS_CLI epic-sync <epic-id>`.

Then commit: `git add .tasks/ && git commit -m "Tasks: Move #<id> to speccing"`

**Step 2 — Interactive solicitation (LLM):**

Ask guiding questions to fill in the 6 required sections in `spec.md` (Description, Motivation, Scope, Constraints, Changes, Acceptance Criteria). Iterate as many times as needed — never rush the user toward planning. Only the user decides when the spec is complete.

**All decisions in the spec:** Every change must be fully defined during speccing — exact files, exact changes, no ambiguity. Never defer decisions to planning or label anything a "planning detail." Planning builds an execution plan for changes already decided here.

**Self-sufficiency check:** After each round of user input, re-read `spec.md` and actively check for:
- **Gaps:** Changes referenced in acceptance criteria but missing from the Changes table (or vice versa). Scope items with no corresponding change.
- **Contradictions:** Constraints that conflict with proposed changes. Scope "out of scope" items that overlap with listed changes.
- **Ambiguity:** Changes described vaguely enough that two people could interpret them differently.
If any issues are found, raise them as open questions — one at a time, resolved before moving on. Do not suggest moving to planning while open questions exist.

**Epic consistency during solicitation:** If the task has `parent_epic`, run the Epic Sync consistency check after each substantive spec change (title, scope, description). See [workflows.md](workflows.md) for the full Epic Sync procedure.

**Proactive epic suggestion:** During solicitation, if any of these signals appear, suggest creating an epic:
- The Changes table grows beyond ~8 files or spans 3+ distinct areas
- The user describes multiple loosely-related changes that could ship independently
- Acceptance criteria divide into natural groups with no cross-dependencies
- The estimated scope clearly exceeds a single reviewable PR

When suggesting, explain: "This task is growing large. Consider converting it to an **epic** with smaller child tasks that can be specced, planned, and reviewed independently. I can create the epic and break this into N child tasks — want me to?" If the user agrees, use the CLI: `python3 $TASKS_CLI add-epic <title>` for the parent and `python3 $TASKS_CLI add-to-epic <epic-id> <description>` for each child.

**Never suggest planning prematurely.** Do not prompt the user to move to planning. When the user signals the spec is ready, run the validation gate. If it fails, explain what's missing and continue iterating.

---

### Start Planning

```
/tasks plan <id>
```

**Precondition:** Task must be in `speccing` status. If not, refuse with: "Task #<id> must be specced before planning. Use `/tasks spec <id>` first."

**Speccing validation gate:** Before transitioning, verify:
1. All 6 required sections (Description, Motivation, Scope, Constraints, Changes, Acceptance Criteria) have meaningful content — not trivial one-liners or placeholders.
2. Every acceptance criterion has an external verification method (a command, test, grep, or observable output) — not just "Claude reads the file and confirms."
3. **Self-sufficiency:** The spec requires no further research to understand what changes to make. Every change is fully defined — exact files, exact behavior, no TBD items.
4. **Internal consistency:** No contradictions between sections (e.g., scope vs. changes, constraints vs. changes). Every acceptance criterion maps to a change; every change maps to an acceptance criterion.
5. **No open questions remain.**
If any check fails, refuse with details.

**Phase 1 — Transition (CLI + manual plan.md creation):**

1. **Run:** `python3 $TASKS_CLI transition <id> planning`
2. Create empty `plan.md` skeleton in the task folder (frontmatter + headings only, no content). See [schemas.md](schemas.md) for the plan template.
3. If `data.epic_sync_needed` is present, run `python3 $TASKS_CLI epic-sync <epic-id>`
4. Commit: `git add .tasks/ && git commit -m "Tasks: Move #<id> to planning"`

**Phase 2 — Build execution plan (only after commit completes):**
5. Research the codebase and write the execution plan in `plan.md` — sequencing, step-by-step implementation order, and test plan for the changes already defined in the spec. Do not redefine what changes to make; that belongs in the spec.
6. If planning reveals spec gaps (missing files, unclear changes), update `spec.md` directly (never plan.md) and commit as a planning-phase spec update. This should be rare — a well-specced task needs no planning-phase amendments.

Output clickable link: `[plan.md](.tasks/items/2-planning/<id>/plan.md)`

---

### Mark Plan Review

```
/tasks plan-review <id>
```

**Run:** `python3 $TASKS_CLI transition <id> plan-review`

If `data.epic_sync_needed` is present, run `python3 $TASKS_CLI epic-sync <epic-id>`.

Commit: `git add .tasks/ && git commit -m "Tasks: Move #<id> to plan-review"`

---

### Start Implementing

```
/tasks implement <id>
```

**Step 1 — Transition (CLI):**

**Run:** `python3 $TASKS_CLI transition <id> implementing`

If `data.epic_sync_needed` is present, run `python3 $TASKS_CLI epic-sync <epic-id>`.

Commit: `git add .tasks/ && git commit -m "Tasks: Move #<id> to implementing"`

**Step 2 — Create branch and worktree (manual):**

```bash
git branch feature/task-<id>-<slug>
mkdir -p .worktrees/task-<id>
git worktree add .worktrees/task-<id>/ feature/task-<id>-<slug>
```

Report the created worktree path to the user.

**Step 3 — Create impl.md:**

Create `impl.md` in the task folder with frontmatter and header (run `date -u '+%Y-%m-%d %H:%M UTC'` for the timestamp):

```markdown
---
created: YYYY-MM-DD HH:MM UTC
---

# Implementation Report: Task #<id>
```

**Step 4 — Implement (Iteration 1):** Read `plan.md` and begin executing it step by step. Do NOT stop and wait for user instruction. **Proceed directly into implementation.**

When the iteration is done, append the iteration section to `impl.md` (see [schemas.md](schemas.md) for template) with:
- Changes made (file diff stats + descriptions)
- Acceptance criteria results (pass/fail per criterion from spec.md)
- Status: `current`

Then **offer the user a devil's advocate review**: "Want me to run a devil's advocate review? A fresh subagent will assume this iteration is wrong and look for what's broken."

**Devil's advocate subagent:** If the user accepts, launch a fresh Agent subagent:

```
You are a devil's advocate reviewer for task #<id>, iteration <N>.
ASSUME the implementation is wrong. Your job is to find what's broken.

Read these files:
- .tasks/items/<status-dir>/<id>/spec.md (the specification)
- .tasks/items/<status-dir>/<id>/plan.md (the execution plan)
- .tasks/items/<status-dir>/<id>/impl.md (the implementation report)

Then examine the actual code changes in the worktree at .worktrees/task-<id>/.

Look for:
1. Spec violations: Does the code actually do what the spec says? Check each acceptance criterion.
2. Missing changes: Are there items in the spec's Changes table that weren't implemented?
3. Unplanned changes: Are there code changes that don't trace back to the spec?
4. Edge cases: What inputs/states could break this implementation?
5. Test gaps: Are there behaviors that should be tested but aren't?

Return a JSON verdict:
{
  "pass": true/false,
  "findings": [
    {"severity": "error|warning", "description": "...", "location": "file:line or spec:section"}
  ],
  "summary": "one-line overall assessment"
}
```

If the devil's advocate finds errors, append its findings to the iteration in `impl.md`, mark the iteration as `superseded`, and begin a new iteration addressing the findings. Repeat until the devil's advocate passes or the user decides to stop.

**IMPORTANT:** Never implement on main. Never merge or delete any worktree until `/tasks complete`.

---

### Submit for Review

```
/tasks review <id>
```

**Step 1 — Generate review file (CLI):**

**Run:** `python3 $TASKS_CLI review <id>`

The CLI generates `revw.md` with frontmatter and a file summary table. Parse JSON output for stats.

**Step 2 — Ask user** if they want a detailed change report (expands `revw.md` with full diffs). If yes, generate per-file diffs manually and append to `revw.md` (this part requires LLM judgment for descriptions).

**Step 3 — Transition (CLI):**

**Run:** `python3 $TASKS_CLI transition <id> reviewing`

If `data.epic_sync_needed` is present, run `python3 $TASKS_CLI epic-sync <epic-id>`.

Commit: `git add .tasks/ && git commit -m "Tasks: Move #<id> to reviewing"`

**IMPORTANT:** Never merge or delete any worktree until `/tasks complete`.

---

### Complete Task

```
/tasks complete <id>
```

**Run:** `python3 $TASKS_CLI complete <id>`

The CLI handles the full workflow:
1. Verifies no uncommitted changes in worktree
2. Merges feature branch into main
3. Removes worktree and deletes branch
4. Moves task to `6-complete/`
5. Updates frontmatter with `completed` datetime
6. Rebuilds INDEX.md
7. Commits

Check `data.epic_sync_needed` and run `python3 $TASKS_CLI epic-sync <epic-id>` if present, then commit the epic update.

Check `warnings` for any issues (e.g., missing revw.md).

---

### Reject Task

```
/tasks reject <id> [reason]
```

**Run:** `python3 $TASKS_CLI reject <id> <reason>`

If no reason is provided by the user, ask for one before running the CLI — a reason is always required.

Check `data.epic_sync_needed` and run `python3 $TASKS_CLI epic-sync <epic-id>` + commit if present.

---

### Consolidate Tasks

```
/tasks consolidate <id> into <target-id>
```

**Run:** `python3 $TASKS_CLI consolidate <id> <target-id>`

The CLI moves the source task, updates frontmatter, preserves original content, rebuilds INDEX.md, and commits.

Check `data.epic_sync_needed` and run `python3 $TASKS_CLI epic-sync <epic-id>` + commit if present.

---

### Migrate Legacy Layout

```
/tasks migrate
```

**Run:** `python3 $TASKS_CLI migrate`

The CLI detects status directories (0-inbox, 1-speccing, etc.) that exist directly under `.tasks/` instead of under `.tasks/items/`, moves them into `items/`, rebuilds INDEX.md, and commits.

**When to offer:** The `list` and `audit` commands include a warning when legacy layout is detected. When you see this warning, tell the user their project uses the old layout and offer to run `/tasks migrate` to update it. Do not migrate automatically — always ask first.

---

### Install Viewer

```
/tasks install-viewer
```

Builds and installs the Tasks Viewer VS Code extension — a sidebar webview that displays the `.tasks/` backlog with clickable tasks that open rendered detail panels.

```bash
python3 "$TASKS_CLI" install-viewer
```

Report the result to the user. Remind them to reload VS Code.

---

### Uninstall Viewer

```
/tasks uninstall-viewer
```

Removes the Tasks Viewer VS Code extension from the local VS Code installation.

```bash
python3 "$TASKS_CLI" uninstall-viewer
```

Report the result to the user. Remind them to reload VS Code.

---

### Audit Backlog

```
/tasks audit
```

**Step 1 — Structural checks (CLI):**

**Run:** `python3 $TASKS_CLI audit`

The CLI returns JSON with `data.errors`, `data.warnings`, and `data.summary`. Format these into a readable report.

**Step 2 — Obsolete task detection (LLM):**

For each open task (inbox, planning, plan-review), compare against completed tasks:
- Does a completed task's description overlap significantly with this open task?
- Does a completed task explicitly address the same problem?
- Has the area this task targets been redesigned or replaced?

This requires LLM judgment and cannot be done by the CLI.

**Output:** Write the combined report (CLI checks + obsolete analysis) to `.temp/tasks-audit-<datetime>.md`.

---

## Critic Gate

**MANDATORY:** Before every status transition, launch a **critic subagent** with a clean context window to review the work completed in the current phase. The critic catches gaps, inconsistencies, and contradictions that the working agent has gone blind to.

**When to run:** After the user requests a transition (e.g., `/tasks plan`, `/tasks review`, `/tasks complete`) but **before** executing the CLI transition command. The critic must pass before the transition proceeds.

**How to run:** Use the Agent tool to launch a fresh subagent with:
- A clear description of what phase just completed and what to verify
- The relevant files to read (task.yaml, spec.md, plan.md, impl.md, revw.md)
- Explicit instructions to look for gaps, inconsistencies, and contradictions
- Instructions to return a structured verdict

**Critic prompt template:**

```
You are a critic reviewing task #<id> before transitioning from <current-phase> to <next-phase>.

Read these files:
- .tasks/items/<status-dir>/<id>/task.yaml (metadata)
- .tasks/items/<status-dir>/<id>/spec.md (specification)
- .tasks/items/<status-dir>/<id>/plan.md (if exists)
- .tasks/items/<status-dir>/<id>/impl.md (if exists)
- .tasks/items/<status-dir>/<id>/revw.md (if exists)

Check for:
1. GAPS: Are there acceptance criteria with no corresponding change? Changes with no acceptance criterion? Scope items with no implementation?
2. INCONSISTENCIES: Do the spec, plan, and implementation agree on what was done? Are there contradictions between sections?
3. CONTRADICTIONS: Do constraints conflict with changes? Does the plan contradict the spec? Do completed changes match what was planned?
4. COMPLETENESS: Has every item in the plan/spec been addressed? Are there TODO/FIXME/placeholder items left?

Return a JSON verdict:
{
  "pass": true/false,
  "findings": [
    {"severity": "error|warning", "description": "...", "location": "file:section"}
  ],
  "summary": "one-line overall assessment"
}
```

**Phase-specific checks:**

| Transition | Critic focus |
|------------|-------------|
| speccing → planning | Spec completeness: all 6 sections filled, no ambiguity, acceptance criteria are externally verifiable, changes are fully specified |
| planning → plan-review | Plan covers every change in spec, sequencing is logical, test plan addresses every acceptance criterion |
| plan-review → implementing | Plan is actionable, no open questions, dependencies are ordered correctly |
| implementing → reviewing | Every planned change is implemented, no unplanned changes snuck in, acceptance criteria are met, no leftover TODOs |
| reviewing → complete | All review feedback addressed, revw.md is accurate, no regressions |

**On failure:** Report the findings to the user. Do NOT proceed with the transition. The user decides whether to fix the issues or override.

**On pass with warnings:** Report the warnings to the user alongside the transition. Proceed only if the user confirms.

---

## User Approval Rule

**CRITICAL:** Each `/tasks` command is a standalone operation. After executing the requested command, **STOP and return control to the user**. NEVER chain commands or advance a task to the next status without explicit user approval.

- `/tasks add` → add to inbox, commit, stop. Do NOT proceed to spec.
- `/tasks spec` → move to speccing (or back-transition), run solicitation, stop. Do NOT proceed to plan.
- `/tasks plan` → move to planning, create plan, commit, stop. Do NOT proceed to plan-review/implement.
- `/tasks plan-review` → move to plan-review, commit, stop. Do NOT proceed to implement.
- `/tasks implement` → move to implementing, create branch, commit, then **proceed directly into implementation** using `plan.md`. When implementation is done, **STOP and report back**. Do NOT transition to reviewing.

The user decides when to advance between phases. Always wait for their explicit instruction. The `/tasks implement` exception only applies to starting the coding work — it does NOT grant permission to transition to reviewing or complete afterward.

**No phase skipping without challenge:** The lifecycle is strictly sequential: inbox → speccing → planning → plan-review → implementing → reviewing → complete. Skip-forward transitions (e.g., inbox → implementing for quick fixes) are allowed only after challenging the user: "This task hasn't been specced/planned — are you sure?" Require explicit confirmation before proceeding. When skipping, pass `--force` to the CLI: `python3 $TASKS_CLI transition <id> <status> --force`. After `/tasks add`, do not offer to go "straight to planning" — the default next step is always speccing.

**Branch isolation:** When working inside a feature branch or worktree, only modify the task associated with that branch. Never touch other tasks. Never create new tasks in a feature branch — create and commit them directly on main.

---

## Quick Reference

- **CLI tool:** `python3 $TASKS_CLI <command>` — handles all mechanical file/git operations with JSON output
- **Task numbering:** Permanent IDs, never reused. Find highest + 1.
- **Sort order:** All INDEX.md sections are sorted by task ID **descending** (newest first). Maintain this when adding, moving, or reordering tasks.
- **Commit every transition:** Use `Tasks:` prefix
- **Inbox first:** New tasks → inbox, prioritize later
- **Worktree lifecycle:** Created by `/tasks implement`, removed by `/tasks complete`
- **Preserve content:** Never lose original content when consolidating/rejecting
- **Branch isolation:** Feature branches only modify their associated task; new tasks go on main
- **Viewer extension:** `install-viewer` builds and installs the VS Code sidebar; `uninstall-viewer` removes it. Reload VS Code after either.
- **Epic Sync (mandatory):** When `data.epic_sync_needed` is present in CLI output, run `python3 $TASKS_CLI epic-sync <id>` and commit the result. Never skip this.
- **Real timestamps only:** The CLI handles timestamps automatically. When writing files manually (e.g., plan.md), run `date -u '+%Y-%m-%d %H:%M UTC'` for actual time — never invent dates.

**Task files:** `task.yaml` (metadata) + `spec.md` (specification) + `plan.md` (execution plan) + `impl.md` (implementation iterations) + `revw.md` (review notes)

**Full documentation:**
- [schemas.md](schemas.md) - File schemas and templates (task.yaml, spec.md, plan.md, impl.md, revw.md)
- [workflows.md](workflows.md) - Detailed command workflows
- [reference.md](reference.md) - Best practices and lifecycles
