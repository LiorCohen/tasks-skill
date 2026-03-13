# Task Management Workflows

Detailed workflows for each task command. Mechanical operations use the `tasks_cli.py` CLI tool. LLM-requiring operations (solicitation, planning, implementation, semantic analysis) are described inline.

**CLI convention:** All CLI commands output structured JSON. Parse `data.*` fields for results and check for `data.epic_sync_needed` after every command. Commands that don't auto-commit (transition, sync-index, review, epic-sync) need a manual `git add .tasks/ && git commit` after.

---

## View Backlog

```
User: /tasks
User: /tasks list
```

**Run:** `python3 $TASKS_CLI list`

Parse `data.tasks` array and render as a markdown table. The CLI returns tasks pre-sorted (active statuses first, then inbox by priority, then by ID descending). Use `data.summary` for the summary line. See SKILL.md for table formatting (status/priority emoji, type column, epic children display).

Skip empty sections. Omit Completed, Rejected, and Consolidated sections (archival). Never truncate or summarize rows.

---

## View Single Task

```
User: /tasks 19
```

**Action:** Read `items/<status-dir>/19/task.yaml` for metadata and `items/<status-dir>/19/spec.md` for the full specification.

---

## Add New Task

```
User: /tasks add <description>
User: /tasks add epic <description>
```

**Run:** `python3 $TASKS_CLI add <description>` or `python3 $TASKS_CLI add-epic <description>`

The CLI handles everything: creates folder, writes `task.yaml` + `spec.md`, rebuilds INDEX.md, commits.

Parse `data.id` and confirm: "Created task #N in inbox."

New tasks always go to inbox first. User can prioritize later.

---

## Add Task to Epic

```
User: /tasks add-to-epic <epic-id> <description>
```

**Run:** `python3 $TASKS_CLI add-to-epic <epic-id> <description>`

The CLI verifies the epic exists, creates the child task with `parent_epic` and `priority: inherit`, updates the epic's Children table, rebuilds INDEX.md, and commits.

Parse `data.id` and confirm: "Created task #N under epic #E."

**IMPORTANT:** When a child task changes status or its content changes, run the **Epic Sync** procedure (see below).

---

## Epic Sync

**Trigger:** Any time a task with `parent_epic` is modified — status transition, spec content change, title change, or scope change.

### Step 1: Update Children table (CLI)

**Run:** `python3 $TASKS_CLI epic-sync <epic-id>`

The CLI reads all child tasks, rebuilds the `## Children` table with current statuses and paths.

### Step 2: Check epic consistency (LLM)

Re-read the epic's Description, Motivation, and Scope sections. Verify they still accurately reflect the collective intent of all children:

- **Description:** Does the epic's description still cover what the children are actually doing? If a child's scope narrowed, broadened, or shifted, the epic description may need adjustment.
- **Motivation:** Does the epic's stated motivation still justify all children? If children were added, removed, or changed direction, update accordingly.
- **Scope — In scope:** Each bullet should map to one or more children. Remove bullets for rejected/consolidated children. Add bullets for newly added children.
- **Scope — Out of scope:** Verify nothing listed as out-of-scope is now covered by a child (or vice versa).
- **Acceptance Criteria:** Verify they still reflect the current set of children and their combined outcome.

If inconsistencies are found, **update the epic's sections in place** to stay aligned. Keep the epic as the authoritative summary of its children's collective work.

### Step 3: When to skip

- If the change is trivial (typo fix, formatting) and doesn't affect the child's title, scope, or status — skip the consistency check (step 2). Still run the CLI for the Children table update (step 1).

**Include the epic updates in the same commit as the child change.**

---

## Prioritize Task

```
User: /tasks prioritize 15 high
User: /tasks prioritize 15 medium
User: /tasks prioritize 15 low
```

**Run:** `python3 $TASKS_CLI prioritize <id> <level>`

The CLI updates `task.yaml`, rebuilds INDEX.md, and commits. If the task has `parent_epic`, the CLI will error — tell the user to prioritize the epic instead.

**Note:** Priority only affects INDEX.md grouping (sub-sections under Inbox), not file location. Tasks with `priority: inherit` always follow their parent epic's priority.

---

## Start Speccing

```
User: /tasks spec 19
```

**Step 1 — Transition (CLI):**

**Run:** `python3 $TASKS_CLI transition <id> speccing`

If `data.epic_sync_needed` is present, run: `python3 $TASKS_CLI epic-sync <epic-id>`

Commit: `git add .tasks/ && git commit -m "Tasks: Move #<id> to speccing"`

**Step 2 — Interactive solicitation (LLM):**

Ask guiding questions to fill in the 6 required sections in `spec.md` (Description, Motivation, Scope, Constraints, Changes, Acceptance Criteria). Iterate as many times as needed — never rush the user toward planning. Only the user decides when the spec is complete.

**All decisions in the spec:** Every change must be fully defined during speccing — exact files, exact changes, no ambiguity. Never defer decisions to planning or label anything a "planning detail." Planning builds an execution plan for changes already decided here.

**Self-sufficiency check:** After each round of user input, re-read `spec.md` and actively check for:
- **Gaps:** Changes referenced in acceptance criteria but missing from the Changes table (or vice versa). Scope items with no corresponding change.
- **Contradictions:** Constraints that conflict with proposed changes. Scope "out of scope" items that overlap with listed changes.
- **Ambiguity:** Changes described vaguely enough that two people could interpret them differently.
If any issues are found, raise them as open questions — one at a time, resolved before moving on. Do not suggest moving to planning while open questions exist.

**Epic consistency during solicitation:** If the task has `parent_epic`, run the Epic Sync procedure (CLI step 1 + LLM step 2) after each substantive spec change — title change, scope change, or description rewrite. Include epic updates in the same commit as the spec update.

**Proactive epic suggestion:** During solicitation, watch for signals that the task should become an epic:
- The Changes table grows beyond ~8 files or spans 3+ distinct areas
- The user describes multiple loosely-related changes that could ship independently
- Acceptance criteria divide into natural groups with no cross-dependencies
- The estimated scope clearly exceeds a single reviewable PR

When any signal is detected, suggest: "This task is growing large. Consider converting it to an **epic** with smaller child tasks that can be specced, planned, and reviewed independently. I can create the epic and break this into N child tasks — want me to?"

If the user agrees:
1. `python3 $TASKS_CLI add-epic <title>` (reusing the current task's description/motivation)
2. `python3 $TASKS_CLI add-to-epic <epic-id> <description>` for each sub-task
3. `python3 $TASKS_CLI consolidate <original-id> <epic-id>`

**Never suggest planning prematurely.** Do not prompt the user to move to planning. When the user signals the spec is ready, run the validation gate. If it fails, explain what's missing and continue iterating.

---

## Start Planning

```
User: /tasks plan 19
```

**Precondition:** Task must be in `speccing` status. If not, refuse: "Task #19 must be specced before planning. Use `/tasks spec 19` first."

**Speccing validation gate:** Before transitioning, verify:
1. All 6 required sections (Description, Motivation, Scope, Constraints, Changes, Acceptance Criteria) have meaningful content — not trivial one-liners or placeholders.
2. Every acceptance criterion has an external verification method (a command, test, grep, or observable output) — not just "Claude reads the file and confirms."
3. **Self-sufficiency:** The spec requires no further research to understand what changes to make. Every change is fully defined — exact files, exact behavior, no TBD items.
4. **Internal consistency:** No contradictions between sections (e.g., scope vs. changes, constraints vs. changes). Every acceptance criterion maps to a change; every change maps to an acceptance criterion.
5. **No open questions remain.**
If any check fails, refuse with details.

**Phase 1 — Transition (CLI + manual plan skeleton):**

1. **Run:** `python3 $TASKS_CLI transition <id> planning`
2. Create empty `plan.md` skeleton in the task folder (frontmatter + headings only, no content yet). See [schemas.md](schemas.md) for the plan template.
3. If `data.epic_sync_needed` is present, run: `python3 $TASKS_CLI epic-sync <epic-id>`
4. Commit: `git add .tasks/ && git commit -m "Tasks: Move #<id> to planning"`

**Output:**
```
Task #19 moved to planning status.

Plan: [plan.md](.tasks/items/2-planning/19/plan.md)
```

**Phase 2 — Build execution plan (only after commit completes, LLM):**
5. Research the codebase and write the execution plan in `plan.md` — sequencing, step-by-step implementation order, and test plan for the changes already defined in the spec. Do not redefine what changes to make; that belongs in the spec.
6. If planning reveals spec gaps (missing files, unclear changes), update `spec.md` directly (never plan.md) and commit as a planning-phase spec update. This should be rare — a well-specced task needs no planning-phase amendments.

**IMPORTANT:** The status transition and commit MUST complete before any planning work begins. Do not start researching or writing plan content until the transition is committed.

---

## Mark Plan Review

```
User: /tasks plan-review 19
```

**Run:** `python3 $TASKS_CLI transition <id> plan-review`

If `data.epic_sync_needed` is present, run: `python3 $TASKS_CLI epic-sync <epic-id>`

Commit: `git add .tasks/ && git commit -m "Tasks: Move #<id> to plan-review"`

Use when a task has a complete plan and is ready for plan review before implementation.

---

## Start Implementing

```
User: /tasks implement 19
```

**Step 1 — Transition (CLI):**

**Run:** `python3 $TASKS_CLI transition <id> implementing`

If `data.epic_sync_needed` is present, run: `python3 $TASKS_CLI epic-sync <epic-id>`

Commit: `git add .tasks/ && git commit -m "Tasks: Move #<id> to implementing"`

**Step 2 — Create branch and worktree:**

```bash
git branch feature/task-<id>-<slug>
mkdir -p .worktrees/task-<id>
git worktree add .worktrees/task-<id>/ feature/task-<id>-<slug>
```

Report the created worktree path to the user.

**Step 3 — Create impl.md:**

Create `impl.md` in the task folder:

```markdown
# Implementation Report: Task #<id>
```

**Step 4 — Implement (Iteration 1, LLM):**

**Proceed directly into implementation** — read `plan.md` and begin executing it step by step. Do NOT stop and wait for user instruction.

**IMPORTANT:** Always create a side branch before implementing. Never implement directly on main. The worktree keeps main available in the primary working directory while implementation happens in the worktree.

**NEVER** merge the feature branch or delete any worktree during implementation. All worktrees and branches persist until the task is completed via `/tasks complete`.

### During Implementation

- All implementation work happens in `.worktrees/task-<id>/`
- The branch name follows the pattern `feature/task-<id>-<slug>`

### After Each Iteration

When the iteration is done:

1. **Record the iteration** in `impl.md` — append a new `## Iteration N` section with:
   - Date, branch, status (`current`)
   - Changes Made table (file, added, removed, description)
   - Acceptance Criteria Results (pass/fail per criterion from `spec.md`)

2. **Offer the devil's advocate review**: "Want me to run a devil's advocate review? A fresh subagent will assume this iteration is wrong and look for what's broken."

3. **If the user accepts**, launch a fresh Agent subagent:

```
You are a devil's advocate reviewer for task #<id>, iteration <N>.
ASSUME the implementation is wrong. Your job is to find what's broken.

Read these files:
- .tasks/items/<status-dir>/<id>/spec.md
- .tasks/items/<status-dir>/<id>/plan.md
- .tasks/items/<status-dir>/<id>/impl.md

Then examine the actual code changes in the worktree at .worktrees/task-<id>/.

Look for:
1. Spec violations: Does the code actually do what the spec says?
2. Missing changes: Items in the spec's Changes table that weren't implemented
3. Unplanned changes: Code changes that don't trace back to the spec
4. Edge cases: Inputs/states that could break this implementation
5. Test gaps: Behaviors that should be tested but aren't

Return JSON: {"pass": true/false, "findings": [...], "summary": "..."}
```

4. **If the devil's advocate finds errors:**
   - Append its findings to the current iteration's `### Devil's Advocate Review` section in `impl.md`
   - Mark the iteration as `Status: superseded`
   - Begin a new iteration addressing the findings
   - Repeat until the devil's advocate passes or the user decides to stop

5. **If the devil's advocate passes** (or the user declines the review):
   - Append any warnings to `impl.md`
   - **STOP and return control to the user** — do NOT auto-transition to reviewing

---

## Submit for Review

```
User: /tasks review 19
```

**Step 1 — Generate review file (CLI):**

**Run:** `python3 $TASKS_CLI review <id>`

The CLI generates `revw.md` with frontmatter and a file summary table. Parse `data.files_changed`, `data.total_added`, `data.total_removed` for the summary.

**Step 2 — Ask the user:** "Would you like me to expand the change report with detailed diffs?"

If the user says yes, generate detailed diffs (LLM — requires per-file descriptions):
1. Run `git diff main..HEAD -- ':!.tasks/'`
2. Append per-file sections to `revw.md`, each with:
   - The file path as a heading with a clickable markdown link
   - A one-line description of what changed
   - The actual diff in a syntax-highlighted fenced code block

**Step 3 — Transition (CLI):**

**Run:** `python3 $TASKS_CLI transition <id> reviewing`

If `data.epic_sync_needed` is present, run: `python3 $TASKS_CLI epic-sync <epic-id>`

Commit: `git add .tasks/ && git commit -m "Tasks: Move #<id> to reviewing"`

**NEVER** merge the feature branch or delete the worktree during reviewing. The worktree and branch persist until the task is completed via `/tasks complete`.

**Commit prefixing:** All commits made during the reviewing phase (e.g., fixes from code review) must be prefixed with the task reference (e.g., `Task #19: Fix validation edge case`).

**Amend when possible:** If the previous commit on the feature branch has NOT been pushed to remote, review-phase commits should amend it and update the existing changelog entry. If it HAS been pushed, create a new commit and amend the changelog entry in-place (update the existing version entry, do not create a new one).

---

## Complete Task

```
User: /tasks complete 7
```

**Run:** `python3 $TASKS_CLI complete <id>`

The CLI handles the full workflow: epic completion guard, worktree verification, merge, worktree removal, branch deletion, folder move, metadata update, INDEX.md rebuild, and commit.

If `data.epic_sync_needed` is present, run: `python3 $TASKS_CLI epic-sync <epic-id>`, then commit: `git add .tasks/ && git commit -m "Tasks: Sync epic #<epic-id>"`

Check `warnings` for any issues (e.g., missing revw.md).

---

## Reject Task

```
User: /tasks reject 15
User: /tasks reject 15 "Out of scope for MVP"
```

**Determine the reason for rejection** before running the CLI. A reason is always required:
- If the user says "obsolete", check completed tasks to identify which task(s) made it obsolete. Reference them in the reason (e.g., "Obsolete — superseded by #81")
- If the reason is unclear, **ask the user** before proceeding

**Run:** `python3 $TASKS_CLI reject <id> <reason>`

The CLI moves the task, updates `task.yaml` and spec heading, rebuilds INDEX.md, and commits.

If `data.epic_sync_needed` is present, run: `python3 $TASKS_CLI epic-sync <epic-id>`, then commit the epic update.

---

## Consolidate Tasks

```
User: /tasks consolidate 28 into 27
```

**Run:** `python3 $TASKS_CLI consolidate <source-id> <target-id>`

The CLI moves the source task to consolidated, updates `task.yaml`, preserves original spec content, rebuilds INDEX.md, and commits.

If `data.epic_sync_needed` is present, run: `python3 $TASKS_CLI epic-sync <epic-id>`, then commit the epic update.

---

## Audit Backlog

```
User: /tasks audit
```

**Step 1 — Structural checks (CLI):**

**Run:** `python3 $TASKS_CLI audit`

Parse `data.errors`, `data.warnings`, and `data.summary` from the JSON output.

**Step 2 — Possibly obsolete tasks (LLM):**

For each open task (inbox, planning, plan-review), compare against completed tasks:
- Does a completed task's description overlap significantly with this open task?
- Does a completed task explicitly address the same problem?
- Has the area this task targets been redesigned or replaced?
- Check `depends_on` references: if a dependency was rejected or consolidated, the task may need updating
- Flag tasks with stale priorities or outdated descriptions based on recent completions

This check requires LLM judgment — the CLI cannot do semantic comparison.

**Output format:** Write the combined report to `.temp/tasks-audit-<datetime>.md`:

```markdown
# Tasks Audit — YYYY-MM-DD_HH-MM

## Errors (must fix)
- [ ] #14: task.yaml `status: inbox` but task is in `7-rejected/` directory
- [ ] INDEX.md references #99 but no task folder exists

## Warnings (should fix)
- [ ] #83: Rejected without `rejected_reason` in task.yaml
- [ ] #16: `depends_on: [15]` but #15 was consolidated into #64

## Possibly Obsolete
- [ ] #70: "Git checkpoint workflow" — may be superseded by #49 (Auto-commit hook ✓)
- [ ] #33: "Tests are not useful" — may be addressed by #68 (Plans focus on WHAT ✓)

## Info
- 27 open tasks, 16 completed, 4 rejected, 15 consolidated
- Oldest open task: #3 (created 2026-01-20)
```

**IMPORTANT:** The "Possibly Obsolete" section requires judgement. Read the description of each open task and compare against completed tasks to identify potential overlap. When uncertain, flag it with a `?` and brief rationale so the user can decide. Never auto-reject — only flag for review.

---

## Transition Protocol

Every status transition follows this sequence:

```
1. User requests transition
2. Run critic subagent (clean context) → pass/fail
3. Report findings to user
4. If pass: execute CLI transition + commit
5. If fail: stop, user decides how to proceed
```

### Critic Subagent

Before every transition, launch a **fresh Agent subagent** to review the outgoing phase's work. The subagent gets a clean context window — no prior conversation state — so it evaluates the artifacts independently.

**Launch pattern:**

```
Agent tool:
  description: "Critic: task #<id> <from> → <to>"
  prompt: <see below>
```

**Critic prompt — adapt per transition:**

```
You are a critic reviewing task #<id> before it transitions from <current-phase> to <next-phase>.
Your job: find gaps, inconsistencies, and contradictions. Be thorough but not pedantic.

Read these files:
- <path to task.yaml> (metadata)
- <path to spec.md> (specification)
- <path to plan.md> (if exists)
- <path to impl.md> (if exists)
- <path to revw.md> (if exists)

Phase-specific checks:
<insert the relevant checks from the table below>

General checks (always):
- Do all sections reference the same set of changes/files? Flag any that appear in one section but not another.
- Are there contradictions between sections (e.g., scope says X is out, but changes include X)?
- Are there TODOs, TBDs, placeholders, or "will be determined later" items?
- Is there anything ambiguous enough that two engineers would interpret it differently?

Return your findings as JSON:
{
  "pass": true/false,
  "findings": [
    {"severity": "error|warning", "description": "...", "location": "file:section"}
  ],
  "summary": "one-line overall assessment"
}

"pass" is false if there are any "error" severity findings. Warnings alone still pass.
Do NOT read any other files besides the ones listed above. Do NOT fix anything — only report.
```

**Phase-specific checks to insert:**

| Transition | Checks |
|------------|--------|
| speccing → planning | All 6 required sections have meaningful content (not one-liners). Every acceptance criterion has an external verification method. Every change is fully specified — exact files, exact behavior. No open questions. Every acceptance criterion maps to a change and vice versa. |
| planning → plan-review | Plan covers every change listed in the spec. Sequencing is logical (dependencies come before dependents). Test plan has a verification step for every acceptance criterion. No steps reference files/APIs that don't exist in the spec. |
| plan-review → implementing | Plan is actionable — each step is concrete enough to execute without further research. No open questions or decision points deferred to "implementation time." Dependencies between steps are ordered correctly. |
| implementing → reviewing | Every step in plan.md has been addressed. No unplanned changes snuck in (changes not traceable to the spec). Acceptance criteria from spec.md are met by the implementation. impl.md records all iterations. No leftover TODOs/FIXMEs in changed files. |
| reviewing → complete | All review feedback has been addressed. revw.md accurately reflects what was done. No regressions introduced. Acceptance criteria still pass after review-phase fixes. |

### Handling Critic Results

**Pass (no errors, maybe warnings):**
- Report warnings to the user if any
- Proceed with the CLI transition command

**Fail (has errors):**
- Report all findings to the user
- Do NOT execute the transition
- The user decides: fix the issues, or override with explicit confirmation ("proceed anyway")

**User override:** If the user says "proceed anyway" or "ignore the critic," execute the transition. The critic is a gate, not a veto — the user always has final say.

---

## Command Reference Table

Quick reference for which CLI command maps to each user instruction:

| User instruction | CLI command | Additional steps |
|------------------|------------|------------------|
| "Spec task 19" / "Flesh out #19" | `transition <id> speccing` | Begin solicitation on spec.md |
| "Plan task 19" / "Create a plan for #19" | Critic → `transition <id> planning` | Create plan.md, research, write plan |
| "Task 19 is ready for plan review" | Critic → `transition <id> plan-review` | — |
| "Let's work on task 19" / "Implement #19" | Critic → `transition <id> implementing` | Create branch + worktree + impl.md, implement with iterations |
| "Task 19 is ready for review" | Critic → `review <id>`, then `transition <id> reviewing` | Generates revw.md |
| "Task 19 is done" / "Complete #19" | Critic → `complete <id>` | — |
| "Reject task 19" | `reject <id> <reason>` | No critic needed |
| "Install the viewer" | `install-viewer` | Remind user to reload VS Code |
| "Uninstall the viewer" | `uninstall-viewer` | Remind user to reload VS Code |

**Note:** The critic gate does NOT apply to:
- `add` / `add-epic` / `add-to-epic` (no prior phase to review)
- `spec` from inbox (no prior work to review — speccing is the first content phase)
- `reject` / `consolidate` (terminal states, not quality-gated)
- `prioritize` (metadata change, not a phase transition)

**Always check for `data.epic_sync_needed` after every CLI call and handle it.**

**Epic Sync:** When modifying a child task (one with `parent_epic`) — whether changing status or content — run the CLI's `epic-sync` for the Children table AND check the epic's description/motivation/scope for consistency (LLM step).

**CRITICAL — Explicit approval required for every transition:** Never transition a task to a new status without the user explicitly requesting it. After completing any phase of work (implementation, review, etc.), **STOP and return control to the user**. Do not assume the next transition — wait for the user to tell you. The only exception is `/tasks implement`, where implementation work begins immediately after the transition, but even then, do NOT auto-transition to reviewing when implementation is done.

Skip-forward transitions are allowed (e.g., inbox → implementing for quick fixes), but Claude must always challenge the user before skipping phases: "This task hasn't been specced/planned — are you sure?" Require explicit confirmation before proceeding.

**Branch isolation:** When working inside a feature branch or worktree, only modify the task associated with that branch. Never touch other tasks. Never create new tasks in a feature branch — create and commit them directly on main.
