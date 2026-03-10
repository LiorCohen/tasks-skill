# Task Management Workflows

Detailed workflows for each task command.

---

## View Backlog

```
User: /tasks
User: /tasks list
```

**Action:** Read INDEX.md and display the index, grouped by section. Always show all tasks in each section with their full titles - never abbreviate or summarize the inbox or other sections. Skip empty sections and omit Completed, Rejected, and Consolidated sections (these are archival). Render each task reference (`#XX`) as a markdown link pointing to its primary file relative to the repo root:
- If task has a plan.md file: link to plan.md, e.g., `[#67](.tasks/2-planning/67/plan.md)`
- Otherwise: link to task.md, e.g., `[#67](.tasks/0-inbox/67/task.md)`

---

## View Single Task

```
User: /tasks 19
```

**Action:** Find and read `<status-dir>/19/task.md`.

---

## Add New Task

```
User: /tasks add <description>
User: /tasks add epic <description>
```

**Workflow:**
1. Determine next task number (highest N + 1 across all status dirs)
2. Create folder `0-inbox/<N>/` with `task.md`. If `epic` keyword is present, include `type: epic` in frontmatter and add an empty `## Children` section
3. Add entry to INDEX.md under Inbox
4. Stage and commit: `git add .tasks/ && git commit -m "Tasks: Add #63"`
5. Confirm with task number

New tasks always go to inbox first. User can prioritize later.

---

## Add Task to Epic

```
User: /tasks add-to-epic <epic-id> <description>
```

**Workflow:**
1. Find the epic task and verify it has `type: epic` in frontmatter. If not, refuse: "Task #<epic-id> is not an epic."
2. Determine next task number (highest N + 1 across all status dirs)
3. Create folder `0-inbox/<N>/` with `task.md` containing `parent_epic: <epic-id>` and `priority: inherit` in frontmatter
4. Update the epic's `## Children` table: add a row for the new task with its ID, title, and status
5. Add entry to INDEX.md under Inbox (place under the same priority sub-section as the parent epic)
6. Stage and commit: `git add .tasks/ && git commit -m "Tasks: Add #<N> to epic #<epic-id>"`

**IMPORTANT:** When a child task changes status or its content changes, run the **Epic Sync** procedure (see below).

---

## Epic Sync

**Trigger:** Any time a task with `parent_epic` is modified — status transition, spec content change, title change, or scope change.

Perform these steps **before committing** (include the epic updates in the same commit as the child change):

### 1. Update Children table

- Read the parent epic's `task.md`
- Find the child's row in the `## Children` table
- Update the **Status** column to the child's current status
- Update the **link path** if the child moved directories (e.g., `../0-inbox/182/task.md` → `../1-speccing/182/task.md`)
- Update the child's **title** in the Task column if it changed

### 2. Check epic consistency

Re-read the epic's Description, Motivation, and Scope sections. Verify they still accurately reflect the collective intent of all children:

- **Description:** Does the epic's description still cover what the children are actually doing? If a child's scope narrowed, broadened, or shifted, the epic description may need adjustment.
- **Motivation:** Does the epic's stated motivation still justify all children? If children were added, removed, or changed direction, update accordingly.
- **Scope — In scope:** Each bullet should map to one or more children. Remove bullets for rejected/consolidated children. Add bullets for newly added children.
- **Scope — Out of scope:** Verify nothing listed as out-of-scope is now covered by a child (or vice versa).
- **Acceptance Criteria:** Verify they still reflect the current set of children and their combined outcome.

If inconsistencies are found, **update the epic's sections in place** to stay aligned. Keep the epic as the authoritative summary of its children's collective work.

### 3. When to skip

- If the change is trivial (typo fix, formatting) and doesn't affect the child's title, scope, or status — skip the consistency check (step 2). Still update the Children table if status changed (step 1).

---

## Prioritize Task

```
User: /tasks prioritize 15 high
User: /tasks prioritize 15 medium
User: /tasks prioritize 15 low
```

**Workflow:**
1. Find task folder
2. If the task has `parent_epic`, refuse: "Task #15 inherits priority from its epic. Prioritize the epic instead."
3. Update `task.md` frontmatter `priority` field
4. If the task has `type: epic`, also update all children with `priority: inherit` — move their INDEX.md entries to the new priority sub-section
5. Move task entry to correct priority sub-section under Inbox in INDEX.md
6. Stage and commit (e.g., `git add .tasks/ && git commit -m "Tasks: Prioritize #15 as high")

**Note:** Priority only affects INDEX.md grouping (sub-sections under Inbox), not file location. Tasks with `priority: inherit` always follow their parent epic's priority.

---

## Start Speccing

```
User: /tasks spec 19
```

**From inbox:**
1. Find task folder in `0-inbox/`
2. Move folder to `1-speccing/`
3. Update `task.md` frontmatter: `status: speccing`
4. Update INDEX.md
5. **Epic Sync:** If task has `parent_epic`, run the Epic Sync procedure
6. Stage and commit (e.g., `git add .tasks/ && git commit -m "Tasks: Move #19 to speccing")
7. Begin interactive solicitation (see below)

**From planning (back-transition for substantial rework):**
1. Find task folder in `2-planning/`
2. Move folder to `1-speccing/`
3. Update `task.md` frontmatter: `status: speccing`
4. Update INDEX.md
5. **Epic Sync:** If task has `parent_epic`, run the Epic Sync procedure
6. Stage and commit (e.g., `git add .tasks/ && git commit -m "Tasks: Move #19 back to speccing")
7. Resume solicitation

**Solicitation:** Ask guiding questions to fill in the 6 required sections (Description, Motivation, Scope, Constraints, Changes, Acceptance Criteria). Iterate as many times as needed — never rush the user toward planning. Only the user decides when the spec is complete.

**All decisions in the spec:** Every change must be fully defined during speccing — exact files, exact changes, no ambiguity. Never defer decisions to planning or label anything a "planning detail." Planning builds an execution plan for changes already decided here.

**Self-sufficiency check:** After each round of user input, re-read the spec and actively check for:
- **Gaps:** Changes referenced in acceptance criteria but missing from the Changes table (or vice versa). Scope items with no corresponding change.
- **Contradictions:** Constraints that conflict with proposed changes. Scope "out of scope" items that overlap with listed changes.
- **Ambiguity:** Changes described vaguely enough that two people could interpret them differently.
If any issues are found, raise them as open questions — one at a time, resolved before moving on. Do not suggest moving to planning while open questions exist.

**Epic consistency during solicitation:** If the task has `parent_epic`, run the Epic Sync consistency check (step 2) after each substantive spec change — title change, scope change, or description rewrite. Include epic updates in the same commit as the spec update.

**Proactive epic suggestion:** During solicitation, watch for signals that the task should become an epic:
- The Changes table grows beyond ~8 files or spans 3+ distinct areas
- The user describes multiple loosely-related changes that could ship independently
- Acceptance criteria divide into natural groups with no cross-dependencies
- The estimated scope clearly exceeds a single reviewable PR

When any signal is detected, suggest: "This task is growing large. Consider converting it to an **epic** with smaller child tasks that can be specced, planned, and reviewed independently. I can create the epic and break this into N child tasks — want me to?"

If the user agrees:
1. Create the epic: `/tasks add epic <title>` (reusing the current task's description/motivation)
2. Create child tasks: `/tasks add-to-epic <epic-id> <description>` for each sub-task
3. Consolidate the original task into the epic: `/tasks consolidate <original-id> into <epic-id>`

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

**Workflow — Phase 1 (transition first, before any planning work):**
1. Find task folder
2. Move folder to `2-planning/`
3. Update `task.md` frontmatter: `status: planning`
4. Create empty `plan.md` skeleton in the task folder (frontmatter + headings only, no content yet)
5. Update INDEX.md
6. **Epic Sync:** If task has `parent_epic`, run the Epic Sync procedure
7. Stage and commit (e.g., `git add .tasks/ && git commit -m "Tasks: Move #19 to planning")

**Output:**
```
Task #19 moved to planning status.

Plan: [plan.md](.tasks/2-planning/19/plan.md)
```

**Workflow — Phase 2 (only after the transition commit completes):**
7. Research the codebase and write the execution plan in `plan.md` — sequencing, step-by-step implementation order, and test plan for the changes already defined in the spec. Do not redefine what changes to make; that belongs in the spec.
8. If planning reveals spec gaps (missing files, unclear changes), update task.md directly (never plan.md) and commit as a planning-phase spec update. This should be rare — a well-specced task needs no planning-phase amendments.

**IMPORTANT:** The status transition and commit MUST complete before any planning work begins. Do not start researching or writing plan content until the transition is committed.

---

## Mark Plan Review

```
User: /tasks plan-review 19
```

**Workflow:**
1. Find task folder
2. Move folder to `3-plan-review/`
3. Update `task.md` frontmatter: `status: plan-review`
4. Update INDEX.md
5. **Epic Sync:** If task has `parent_epic`, run the Epic Sync procedure
6. Stage and commit (e.g., `git add .tasks/ && git commit -m "Tasks: Move #19 to plan-review")

Use when a task has a complete plan and is ready for plan review before implementation.

---

## Start Implementing

```
User: /tasks implement 19
```

**Workflow:**
1. Find task folder
2. Move folder to `4-implementing/`
3. Update `task.md` frontmatter: `status: implementing`
4. Update INDEX.md
5. **Epic Sync:** If task has `parent_epic`, run the Epic Sync procedure
6. Commit the task transition on main (e.g., "Tasks: Move #19 to implementing")
7. Create a feature branch: `git branch feature/task-<id>-<slug>`
8. Create worktree: `mkdir -p .worktrees/task-<id> && git worktree add .worktrees/task-<id>/ feature/task-<id>-<slug>`
9. Report the created worktree path to the user
10. **Proceed directly into implementation** — read `plan.md` and begin executing it step by step. Do NOT stop and wait for user instruction.

**IMPORTANT:** Always create a side branch before implementing. Never implement directly on main. The worktree keeps main available in the primary working directory while implementation happens in the worktree.

**NEVER** merge the feature branch or delete any worktree during implementation. All worktrees and branches persist until the task is completed via `/tasks complete`.

### During Implementation

- All implementation work happens in `.worktrees/task-<id>/`
- The branch name follows the pattern `feature/task-<id>-<slug>`

---

## Submit for Review

```
User: /tasks review 19
```

**Workflow:**
1. Find task folder
2. Generate `changes.md` in the task folder (see **Changes File** below)
3. **Ask the user:** "Would you like me to expand the change report with detailed diffs?"
4. If the user says yes, expand `changes.md` with per-file diffs (see **Detailed Change Report** below)
5. Move folder to `5-reviewing/`
6. Update `task.md` frontmatter: `status: reviewing`
7. Update INDEX.md
8. **Epic Sync:** If task has `parent_epic`, run the Epic Sync procedure
9. Commit the task transition on main (e.g., "Tasks: Move #19 to reviewing")

Use when implementation is complete and ready for review.

### Changes File

The changes file is **always** generated as `changes.md` in the task folder (e.g., `.tasks/5-reviewing/19/changes.md`). It captures **all changes made during the task's lifetime** across all lifecycle stages (planning, implementing, reviewing) — not just the final implementation diff. Task management changes (`.tasks/` folder moves, INDEX.md updates) are excluded.

**How to generate:**
1. Run `git diff main..HEAD --stat -- ':!.tasks/'` to get the file list and line counts (excluding task management files)
2. Run `git diff main..HEAD --numstat -- ':!.tasks/'` to get per-file additions/deletions as numbers
3. Write `changes.md` with frontmatter and a summary table

**Template:**

```markdown
---
generated: YYYY-MM-DD HH:MM UTC
branch: <branch-name>
commits: <count>
---

# Task #<id> — Changes

**Files changed:** <count> (+<total-additions> / -<total-deletions> lines)

| File | Added | Removed |
|------|------:|--------:|
| [`<file-path>`](<file-path>) | +<n> | -<n> |
| [`<file-path>`](<file-path>) | +<n> | -<n> |
```

**Rules:**
- Each file path is a clickable markdown link
- Order files logically (core types first, then modules, then commands, then tests, then version/changelog)
- Added/Removed columns show line counts with `+`/`-` prefixes

### Detailed Change Report

When the user requests a detailed change report, **expand** the existing `changes.md` by appending per-file diff sections below the summary table.

**How to generate:**
1. Run `git diff main..HEAD -- ':!.tasks/'`
2. Append sections to `changes.md`, one per file, each containing:
   - The file path as a heading with a clickable markdown link
   - A one-line description of what changed
   - The actual diff in a syntax-highlighted fenced code block

**Appended sections template:**

```markdown

---

## 1. [`<file-path>`](<file-path>)

<One-line description of what changed.>

\`\`\`diff
<actual diff for this file>
\`\`\`

---

## 2. [`<file-path>`](<file-path>)

...
```

**Rules:**
- One section per changed file, numbered sequentially
- Each heading is a clickable markdown link to the file (e.g., `[src/cli.ts](src/cli.ts)`)
- Each section has the file link, a brief description, and the diff
- Use `diff` as the code fence language for all diffs (provides +/- syntax highlighting)
- For new files where you show the full content instead of a diff, use the file's language for syntax highlighting (e.g., `typescript`, `json`, `yaml`, `markdown`)
- New files show the full content
- Order files logically (same order as the summary table)

**NEVER** merge the feature branch or delete the worktree during reviewing. The worktree and branch persist until the task is completed via `/tasks complete`.

**Commit prefixing:** All commits made during the reviewing phase (e.g., fixes from code review) must be prefixed with the task reference (e.g., `Task #19: Fix validation edge case`).

**Amend when possible:** If the previous commit on the feature branch has NOT been pushed to remote, review-phase commits should amend it and update the existing changelog entry. If it HAS been pushed, create a new commit and amend the changelog entry in-place (update the existing version entry, do not create a new one).

---

## Complete Task

```
User: /tasks complete 7
```

**Epic completion guard:** If the task has `type: epic`, check all children (tasks with `parent_epic: <id>`). If any child is not in `complete`, `rejected`, or `consolidated` status, refuse: "Epic #7 cannot be completed — child tasks #X, #Y are still open." The user must complete or reject all children first.

**Workflow:**
1. Find task folder
2. **Ensure `changes.md` exists** in the task folder. If missing, generate it using the same process as the review step (frontmatter + file summary table — see **Changes File** in the Submit for Review section). For epics, `changes.md` is optional since children carry their own changes.
3. **Worktree** at `.worktrees/task-<id>/`:
   a. **Verify no work is lost:** `git -C .worktrees/task-<id>/ status`
      - If uncommitted changes exist, **stop and warn the user** — do not proceed
   b. Merge feature branch into main: `git checkout main && git merge feature/task-<id>-<slug>`
   c. Remove the worktree: `git worktree remove .worktrees/task-<id>/`
   d. Delete the feature branch only if fully merged: `git branch -d feature/task-<id>-<slug>`
4. Clean up: `rm -rf .worktrees/task-<id>/`
5. Move folder to `6-complete/`
6. Update `task.md` frontmatter: `status: complete`, add `completed` datetime (e.g., `completed: 2026-02-12 14:30 UTC`)
7. Update INDEX.md
8. **Epic Sync:** If task has `parent_epic`, run the Epic Sync procedure
9. Commit the task transition on main (e.g., "Tasks: Complete #7")

---

## Reject Task

```
User: /tasks reject 15
User: /tasks reject 15 "Out of scope for MVP"
```

**Workflow:**
1. Find task folder
2. **Determine the reason for rejection.** A reason is always required:
   - If the user says "obsolete", check completed tasks to identify which task(s) made it obsolete. Reference them in the reason (e.g., "Obsolete — superseded by #81")
   - If the reason is unclear, **ask the user** before proceeding
3. Move folder to `7-rejected/`
4. Update `task.md` frontmatter: `status: rejected`, `rejected_reason: <reason>`
5. Update INDEX.md (include the reason summary after the title, e.g., `— obsolete, superseded by #81`)
6. **Epic Sync:** If task has `parent_epic`, run the Epic Sync procedure
7. Stage and commit (e.g., `git add .tasks/ && git commit -m "Tasks: Reject #15")

---

## Consolidate Tasks

```
User: /tasks consolidate 28 into 27
```

**Workflow:**
1. Find both task folders
2. Move task 28 folder to `8-consolidated/`
3. Update task 28 `task.md`:
   - Update frontmatter: `status: consolidated`, `consolidated_into: 27`
   - Update title to include `→ consolidated into #27`
   - **Preserve ALL original content** (description, acceptance criteria, etc.)
4. Update task 27 `task.md` with consolidated context (add ## Consolidated section referencing #28)
5. Update INDEX.md
6. **Epic Sync:** If either task has `parent_epic`, run the Epic Sync procedure for the parent epic (update Children table for removed/consolidated child)
7. Stage and commit (e.g., `git add .tasks/ && git commit -m "Tasks: Consolidate #28 into #27")

---

## Audit Backlog

```
User: /tasks audit
```

**Action:** Scan all task directories and INDEX.md, check for compliance issues, identify possibly obsolete tasks, and present a report with action items.

**Checks to perform:**

#### 1. Structural Integrity
- Every status directory contains only numbered task folders (and `.gitkeep` if empty)
- Every task folder contains a `task.md` file
- No orphan folders (folders without `task.md`)
- No task folders exist outside recognized status directories
- `.gitkeep` files in empty directories should not be flagged as errors

#### 2. Frontmatter Compliance
- All required fields present (`id`, `title`, `status`, `created`)
- `id` matches the folder name
- `status` matches the directory the task lives in (e.g., `0-inbox/` → `inbox`, `1-speccing/` → `speccing`, `7-rejected/` → `rejected`)
- Rejected tasks have `rejected_reason`
- Consolidated tasks have `consolidated_into`
- Completed tasks have `completed` datetime
- `priority` is a valid value (`low`, `medium`, `high`, `inherit`) or absent. `inherit` is only valid when `parent_epic` is set
- `depends_on` and `blocks` reference task IDs that exist

#### 3. INDEX.md Sync
- Every non-archived task (inbox, speccing, planning, plan-review, implementing, reviewing) appears in INDEX.md
- Every entry in INDEX.md points to a task folder that exists
- Tasks appear in the correct INDEX.md section for their status, and in the correct priority sub-section under Inbox
- Rejected entries include a reason summary
- Consolidated entries include the target task reference

#### 4. Title and Heading Consistency
- Frontmatter `title` matches the `# Task N:` heading in the body
- Completed tasks have `✓` suffix in heading
- Rejected tasks have `✗` suffix in heading
- Consolidated tasks have `→ consolidated into #N` suffix in heading

#### 5. Possibly Obsolete Tasks
- For each open task (inbox, planning, plan-review), compare against completed tasks:
  - Does a completed task's description overlap significantly with this open task?
  - Does a completed task explicitly address the same problem?
  - Has the area this task targets been redesigned or replaced?
- Check `depends_on` references: if a dependency was rejected or consolidated, the task may need updating
- Flag tasks with stale priorities or outdated descriptions based on recent completions

#### 6. Dependency Integrity
- `depends_on` references point to tasks that exist
- `depends_on` does not reference rejected or consolidated tasks (may indicate staleness)
- `blocks` references are reciprocal (if A blocks B, B should depend on A)
- No circular dependencies

**Output format:** Write the report to `.temp/tasks-audit-<datetime>.md` (e.g., `tasks-audit-2026-02-07_14-30.md`) and display a summary to the user. Group findings by severity:

```markdown
# Tasks Audit — YYYY-MM-DD_HH-MM

## Errors (must fix)
- [ ] #14: Frontmatter `status: inbox` but task is in `7-rejected/` directory
- [ ] INDEX.md references #99 but no task folder exists

## Warnings (should fix)
- [ ] #83: Rejected without `rejected_reason` in frontmatter
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

## Automatic Status Updates

When the user gives task-related instructions, **automatically move the task to the appropriate status**:

| User instruction | Inferred status | Action |
|------------------|-----------------|--------|
| "Spec task 19" / "Flesh out #19" | `speccing` | Move to `1-speccing/`, begin solicitation |
| "Plan task 19" / "Create a plan for #19" | `planning` | Move to `2-planning/`, create `plan.md` |
| "Task 19 is ready for plan review" / "Mark #19 plan-review" | `plan-review` | Move to `3-plan-review/` |
| "Let's work on task 19" / "Implement #19" | `implementing` | Move to `4-implementing/`, create branch + worktree |
| "Task 19 is ready for review" / "Submit #19" | `reviewing` | Move to `5-reviewing/` |
| "Task 19 is done" / "Complete #19" | `complete` | Move to `6-complete/`, add completion date |
| "Reject task 19" / "Close #19 as wontfix" | `rejected` | Move to `7-rejected/` |

**Always update both the task folder location AND INDEX.md when status changes.**

**Epic Sync:** When modifying a child task (one with `parent_epic`) — whether changing status or content — run the full Epic Sync procedure: update the Children table AND check the epic's description/motivation/scope for consistency.

**After completing implementation work, automatically move the task to `5-reviewing/`** to signal that implementation is done and ready for user review.

Skip-forward transitions are allowed (e.g., inbox → implementing for quick fixes), but Claude must always challenge the user before skipping phases: "This task hasn't been specced/planned — are you sure?" Require explicit confirmation before proceeding.

**Branch isolation:** When working inside a feature branch or worktree, only modify the task associated with that branch. Never touch other tasks. Never create new tasks in a feature branch — create and commit them directly on main.
