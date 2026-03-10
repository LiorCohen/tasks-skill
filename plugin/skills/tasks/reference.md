# Task Management Reference

Best practices, conventions, and lifecycle documentation.

---

## Task Numbering

- Task numbers are permanent identifiers (never reused)
- Find highest number across ALL subdirs, increment by 1
- Numbers may have gaps (merges, deletions)
- Reference as `#N` or `task N`

---

## Best Practices

1. **Commit every transition** - Every state change (add, plan, plan-review, implement, review, complete, reject, consolidate, prioritize) must be committed immediately. Never leave task changes uncommitted. Use the `Tasks:` prefix (e.g., `git commit -m "Tasks: Move #19 to planning"`)
2. **Verify clean state after every command** - After every `/tasks` command completes, run `git status` to confirm no uncommitted changes remain in `.tasks/`. If any exist, stage and commit them before returning to the user
3. **Inbox first** - New tasks go to inbox, prioritize later
4. **Keep atomic** - One clear outcome per task. If a task grows too large during speccing, convert to an epic
5. **Suggest epics proactively** - During speccing, if a task grows beyond ~8 files, spans 3+ areas, or has independently-shippable parts, suggest converting it to an epic with child tasks
6. **Worktree per task** - `/tasks implement` creates a worktree at `.worktrees/task-<id>/`, keeping main clean
7. **Work in worktrees** - Code changes go in `.worktrees/task-<id>/`, not the main working tree
8. **Never lose work** - Before removing a worktree, always verify all commits are merged and no uncommitted changes exist
9. **Only `/tasks complete` cleans up** - Never merge the feature branch or delete any worktree during implementation or reviewing phases. Only `/tasks complete` may merge, remove worktrees, and delete branches
10. **Consolidate related** - Don't duplicate effort
11. **Preserve on consolidate** - Never lose original task content when consolidating
12. **Update both** - Task folder AND INDEX.md must stay in sync
13. **Add context** - When completing, summarize what was done
14. **Date everything** - Completion dates help track velocity
15. **Branch isolation** - Feature branches only modify their associated task; new tasks go on main
16. **Epic Sync** - When a child task changes status or content, run the full Epic Sync procedure: update the parent epic's Children table AND verify the epic's description, motivation, and scope are consistent with its children. See [workflows.md](workflows.md) for the full procedure

---

## Worktree Layout

During implementation, worktrees are created under `.worktrees/task-<id>/`:

```
.worktrees/
  task-19/                                    # worktree for task 19
```

- A worktree is created per task to isolate implementation from the main branch
- The branch name follows the pattern: `feature/task-<id>-<slug>`

---

## Lifecycles

### Task Lifecycle

```
                  0-inbox/ (open tasks)
                           ↓
                     [/tasks spec]
                           ↓
                     1-speccing/
                           ↓
                     [/tasks plan]
                           ↓
                     2-planning/
                           ↓
                 [/tasks plan-review]
                           ↓
                    3-plan-review/
                           ↓
                  [/tasks implement]
                           ↓
                   4-implementing/
                           ↓
                   [/tasks review]
                           ↓
                    5-reviewing/
                           ↓
                   [/tasks complete]
                           ↓
                     6-complete/

Any status → 8-consolidated/ (if combined with another)
Any status → 7-rejected/ (if irrelevant or out of scope)
```

**Priority** (high/medium/low) can be set at any point and only affects INDEX.md grouping (sub-sections under Inbox).

Plans are execution plans created during the planning phase — they define implementation order and sequencing for changes already fully specified in the spec. They move with their task folder through the lifecycle.

---

## Epic Lifecycle

Epics (`type: epic`) are container tasks. They follow the same status directories but have different rules:

- **Epics don't implement directly.** They have no feature branch or worktree. Their children carry the actual code changes.
- **Epic speccing** defines the overall objective, motivation, scope, and children — not a Changes table. Each child gets its own spec with its own Changes table.
- **Epic completion** requires all children to be in `complete`, `rejected`, or `consolidated` status. Use `/tasks complete <epic-id>` only after all children are resolved.
- **Children are independent.** Each child task follows its own full lifecycle (spec → plan → implement → review → complete). Children can be worked on in any order unless they have explicit `depends_on` relationships.
- **Status tracking.** The epic's `## Children` table shows each child's current status. It is updated whenever a child task transitions.

### When to Create an Epic

Epics are suggested proactively during speccing when:
1. The Changes table grows beyond ~8 files or spans 3+ distinct areas
2. Multiple loosely-related changes could ship independently
3. Acceptance criteria divide into natural groups with no cross-dependencies
4. The scope clearly exceeds a single reviewable PR

### Task Types

| Type | Frontmatter | Has Changes table | Has Children table | Can implement directly |
|------|-------------|-------------------|--------------------|----------------------|
| `change` (default) | `type` omitted | Yes | No | Yes |
| `epic` | `type: epic` | No | Yes | No (children do) |
