# Task File Schemas

Reference documentation for the 5-file task structure.

---

## Task Directory Structure

Each task is a folder named by its ID containing up to 5 files:

```
<id>/
├── task.yaml    # Metadata (always present)
├── spec.md      # Specification (created on add, filled during speccing)
├── plan.md      # Execution plan (created during planning)
├── impl.md      # Implementation report with iteration history (created during implementation)
└── revw.md      # Review notes and change summary (created during review)
```

**`task.yaml`** is the only required file. Others are created as the task progresses through its lifecycle.

---

## task.yaml — Metadata

Pure YAML (no `---` delimiters). Contains only structured metadata, never prose.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | number | yes | Unique task number |
| `title` | string | yes | Short title |
| `type` | enum | no | `epic` or `change`. Default `change` (omit for change tasks). |
| `priority` | enum | no | `low`, `medium`, `high`, `inherit` (unset = unprioritized). `inherit` is only valid with `parent_epic`. |
| `status` | enum | yes | `inbox`, `speccing`, `planning`, `plan-review`, `implementing`, `reviewing`, `complete`, `rejected`, `consolidated` |
| `parent_epic` | number | no | ID of the parent epic (only on child tasks) |
| `created` | datetime | yes | `YYYY-MM-DD HH:MM UTC` — **must run `date -u` to get actual time, never invent** |
| `completed` | datetime | no | `YYYY-MM-DD HH:MM UTC` (set on completion) |
| `consolidated_into` | number | no | Target task ID (set on consolidation) |
| `rejected_reason` | string | no | Reason for rejection (set on rejection) |
| `depends_on` | number[] | no | Task IDs this depends on |
| `blocks` | number[] | no | Task IDs blocked by this |

### Template — New task

```yaml
id: 63
title: Short descriptive title
status: inbox
created: 2026-01-30 14:00 UTC
depends_on: []
blocks: []
```

### Template — Epic

```yaml
id: 175
title: Overhaul authentication system
type: epic
priority: high
status: speccing
created: 2026-02-27 16:00 UTC
```

### Template — Child task (under epic)

```yaml
id: 176
title: Add JWT token refresh
priority: inherit
status: inbox
parent_epic: 175
created: 2026-02-27 16:10 UTC
depends_on: []
blocks: []
```

### Template — Completed task

```yaml
id: 7
title: External spec handling
priority: high
status: complete
created: 2026-01-25 09:00 UTC
completed: 2026-01-28 16:30 UTC
```

### Template — Rejected task

```yaml
id: 15
title: Feature that was rejected
priority: medium
status: rejected
created: 2026-01-20 10:00 UTC
rejected_reason: Out of scope for MVP
```

### Template — Consolidated task

```yaml
id: 28
title: Schema validation skill
priority: medium
status: consolidated
created: 2026-01-20 10:00 UTC
consolidated_into: 27
```

---

## spec.md — Specification

Has YAML frontmatter (created/updated dates). Contains the task description, scope, constraints, changes, and acceptance criteria. Created on task add with minimal content, filled during speccing phase.

### Frontmatter Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `created` | datetime | yes | `YYYY-MM-DD HH:MM UTC` |
| `updated` | datetime | no | `YYYY-MM-DD HH:MM UTC` (last modification) |

### Template — New task (minimal)

```markdown
---
created: 2026-01-30 14:00 UTC
---

# Task 63: Short descriptive title

## Description

Short descriptive title

## Acceptance Criteria

- [ ] TBD
```

### Template — Fully specced task

After speccing, spec.md must have all 6 required sections with meaningful content:

```markdown
---
created: 2026-01-28 10:00 UTC
updated: 2026-01-29 16:00 UTC
---

# Short descriptive title

## Description

What this task does — clear, specific, not a rough sketch.

## Motivation

Why this change is needed. What problem it solves. What breaks without it.

## Scope

### In scope

- Specific change 1
- Specific change 2

### Out of scope

- What this task explicitly does NOT cover

## Constraints

- Technical constraints, compatibility requirements, limits
- Rules that must be followed during implementation

## Changes

Every change must be fully defined here — exact files, exact changes, no ambiguity. Never defer decisions to planning or label anything a "planning detail." The plan builds an execution order for changes decided here.

| File | Change |
|------|--------|
| `path/to/file.md` | What changes and why |
| `path/to/other.ts` | What changes and why |

## Acceptance Criteria

Each criterion must have an external verification method — a command, test, or observable output that proves it works without relying on Claude's self-assessment.

- [ ] Criterion — **verify:** `command or test that proves it`
- [ ] Criterion — **verify:** `command or test that proves it`
```

### Template — Epic spec

Epics do NOT have a Changes section. Each child task defines its own changes independently.

```markdown
---
created: 2026-02-27 16:00 UTC
---

# Overhaul authentication system

## Description

High-level objective that this group of tasks achieves together.

## Motivation

Why this body of work is needed as a cohesive unit.

## Scope

### In scope

- Area 1 (covered by #176)
- Area 2 (covered by #177)

### Out of scope

- What this epic explicitly does NOT cover

## Children

| # | Task | Status |
|---|------|--------|
| [#176](../1-speccing/176/spec.md) | Add JWT token refresh | speccing |
| [#177](../0-inbox/177/spec.md) | Migrate session store to Redis | inbox |

## Acceptance Criteria

- [ ] All child tasks are complete
- [ ] Integration between children is verified
```

### Template — Rejected task spec

```markdown
---
created: 2026-01-20 10:00 UTC
---

# Task 15: Feature that was rejected ✗

<!-- Original content preserved below -->

## Description

[Original description content remains here unchanged]

## Acceptance Criteria

[Original acceptance criteria remain here unchanged]
```

### Template — Consolidated task spec

```markdown
---
created: 2026-01-20 10:00 UTC
---

# Task 28: Schema validation skill → consolidated into #27

<!-- Original content preserved below -->

## Description

[Original description content remains here unchanged]

## Acceptance Criteria

[Original acceptance criteria remain here unchanged]
```

**IMPORTANT:** When rejecting or consolidating, original spec content MUST be preserved in full. Only the heading is modified. Frontmatter is preserved as-is.

---

## plan.md — Execution Plan

Has YAML frontmatter (created/updated dates). Contains the implementation sequence, test plan, and verification steps. Created during planning phase. Defines HOW to execute changes already decided in the spec — never redefines WHAT to change.

### Frontmatter Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `created` | datetime | yes | `YYYY-MM-DD HH:MM UTC` |
| `updated` | datetime | no | `YYYY-MM-DD HH:MM UTC` (last modification) |

### Template

```markdown
---
created: 2026-01-28 10:00 UTC
---

# Plan: Short descriptive title

## Execution Order

Step-by-step implementation sequence. Each step references changes from the spec and describes HOW to implement them, in what order, and with what dependencies.

### Step 1: [Component/area — what to do first]

- Files: `path/to/file.ts`, `path/to/other.ts`
- Why first: no dependencies, other steps build on this
- Implementation approach: brief strategy notes

### Step 2: [Component/area — what to do next]

- Files: `path/to/file.ts`
- Depends on: Step 1
- Implementation approach: brief strategy notes

### Step 3: [Tests]

- Write tests for steps 1–2
- Depends on: Steps 1–2

## Tests

### Unit Tests
- [ ] `test_description_of_behavior`
- [ ] `test_another_behavior`

### Integration Tests
- [ ] `test_components_work_together`

### E2E Tests (if applicable)
- [ ] `test_user_facing_flow`

## Verification

- [ ] Outcome 1 is achieved
- [ ] Outcome 2 is achieved
```

### Plan Content Guidelines

| Include in Plans | Do NOT Include in Plans |
|------------------|-------------------------|
| Execution order and sequencing | Re-stating what changes to make (that's the spec) |
| Implementation strategy per step | Full code implementations |
| Dependencies between steps | Decisions about what to change |
| Brief code snippets as constraints | Line-by-line instructions |
| Test plan | Algorithm details |

**Never redefine changes.** If a plan needs to describe what's changing, the spec is incomplete — go back and update the spec, not the plan.

**Tests are required:** Every plan must include an extensive list of tests. Tests define expected behavior and can be reviewed before implementation begins.

---

## impl.md — Implementation Report

Has YAML frontmatter (created/updated dates). Captures each implementation iteration, including the devil's advocate review. Created when implementation begins, appended with each iteration. Previous iterations are never deleted — they provide history of what was tried and why.

### Frontmatter Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `created` | datetime | yes | `YYYY-MM-DD HH:MM UTC` (when implementation started) |
| `updated` | datetime | no | `YYYY-MM-DD HH:MM UTC` (last iteration added) |

### Template

```markdown
---
created: 2026-02-01 10:00 UTC
---

# Implementation Report: Task #63

## Iteration 1

**Date:** 2026-02-01 10:00 UTC
**Branch:** feature/task-63-auth
**Status:** superseded

### Changes Made

| File | Added | Removed | Description |
|------|------:|--------:|-------------|
| `src/auth.ts` | +45 | -12 | Refactored token validation |
| `src/middleware.ts` | +8 | -3 | Added auth middleware hook |

### Acceptance Criteria Results

- [x] Criterion 1 — passed
- [ ] Criterion 2 — not addressed

### Devil's Advocate Review

**Reviewer:** Subagent (clean context, assumes iteration is wrong)
**Verdict:** fail

**Findings:**
- [error] Token refresh not handled for expired sessions (spec.md:Changes)
- [warning] No test for concurrent refresh race condition (plan.md:Tests)

---

## Iteration 2

**Date:** 2026-02-01 14:30 UTC
**Branch:** feature/task-63-auth
**Status:** current

### Changes Made

| File | Added | Removed | Description |
|------|------:|--------:|-------------|
| `src/auth.ts` | +62 | -12 | Full token lifecycle with refresh |
| `src/auth.test.ts` | +30 | -0 | Race condition and expiry tests |

### Acceptance Criteria Results

- [x] Criterion 1 — passed
- [x] Criterion 2 — passed

### Devil's Advocate Review

**Reviewer:** Subagent (clean context, assumes iteration is wrong)
**Verdict:** pass

**Findings:**
- [warning] Error message in line 47 could be more descriptive (minor)
```

### Iteration Rules

1. **Each iteration gets its own section** (`## Iteration N`). Never modify previous iterations — append new ones.
2. **Status values:** `current` for the latest iteration, `superseded` for all previous ones. Only one iteration can be `current` at a time.
3. **Devil's advocate review** is optional but offered to the user after each iteration. The subagent runs with a clean context window, assumes the iteration is wrong, and tries to find what's broken.
4. **Changes Made** table captures the diff stats for that iteration — what was actually changed, not what was planned.
5. **Acceptance Criteria Results** maps each spec criterion to pass/fail for that iteration.

---

## revw.md — Review Notes

Has YAML frontmatter (generated date, branch, stats). Contains the final change summary, acceptance criteria results, and review notes. Created when the task moves to reviewing.

### Frontmatter Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `generated` | datetime | yes | `YYYY-MM-DD HH:MM UTC` |
| `branch` | string | yes | Feature branch name |
| `commits` | number | yes | Number of commits on branch |
| `iterations` | number | yes | Number of implementation iterations |

### Template

```markdown
---
generated: 2026-02-12 14:30 UTC
branch: feature/task-63-auth
commits: 8
iterations: 2
---

# Review: Task #63

## Summary

**Files changed:** 8 (+142 / -37 lines)
**Iterations:** 2

| File | Added | Removed |
|------|------:|--------:|
| [`src/auth.ts`](src/auth.ts) | +62 | -12 |
| [`src/auth.test.ts`](src/auth.test.ts) | +30 | -0 |

## Acceptance Criteria — Final

- [x] Criterion 1 — **verify:** `npm test -- auth`
- [x] Criterion 2 — **verify:** `npm test -- auth.race`

## Review Notes

_(Filled during review phase — reviewer observations, requested changes, sign-off)_
```

### Detailed Change Report (appended on user request)

When the user requests a detailed change report, append per-file diff sections below:

```markdown
---

## 1. [`src/auth.ts`](src/auth.ts)

Refactored token validation and added refresh flow.

\`\`\`diff
<actual diff for this file>
\`\`\`

---

## 2. [`src/auth.test.ts`](src/auth.test.ts)

Added race condition and expiry tests.

\`\`\`diff
<actual diff for this file>
\`\`\`
```

---

## INDEX.md Index Structure

Active tasks (planning through reviewing) have their own top-level sections. Inbox tasks are grouped by priority as sub-sections under Inbox.

```markdown
# Tasks Backlog

---

## Speccing

- [#63](1-speccing/63/): New feature idea

---

## Planning

- [#19](2-planning/19/plan.md): Task management skill

---

## Plan Review

- [#20](3-plan-review/20/): Plugin installation debugging

---

## Implementing

- [#60](4-implementing/60/): Standardize TypeScript imports

---

## Reviewing

- [#55](5-reviewing/55/): Split CHANGELOG.md

---

## Inbox

### High Priority

- [#59](0-inbox/59/): Audit and update agents

### Medium Priority

- [#10](0-inbox/10/): Missing /sdd-help command

### Low Priority

- [#3](0-inbox/3/): Docs missing: CMDO Guide

### Unprioritized

- [#64](0-inbox/64/): Another idea

---

## Complete

- [#62](6-complete/62/): Unified CLI system ✓ (2026-01-30)

---

## Rejected

- [#5](7-rejected/5/): Out of scope feature

---

## Consolidated

- [#28](8-consolidated/28/) → #27
```

**Note:** Links point to task folders. Priority is determined by the `priority` field in task.yaml. Priority sub-sections only appear under Inbox.
