"""Lifecycle commands: transition, prioritize, complete, reject, consolidate."""

from __future__ import annotations

import re
import shutil
import subprocess

from .constants import STATUS_DIRS
from .helpers import (
    collect_all_tasks,
    find_task,
    find_tasks_root,
    get_repo_root,
    get_utc_now,
    git,
    git_add_and_commit,
    slugify,
)
from .index import build_index
from .io import read_meta, write_meta
from .output import error_exit, output_success


def cmd_transition(args):
    """Move task to a new status directory and update metadata."""
    tasks_root = find_tasks_root()
    task_id = args.id
    target_status = args.status

    current_status, task_path = find_task(tasks_root, task_id)

    if current_status == target_status:
        output_success("transition", {
            "id": task_id,
            "from_status": current_status,
            "to_status": target_status,
            "changed": False,
        })
        return

    # Move folder
    target_dir = tasks_root / STATUS_DIRS[target_status] / str(task_id)
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(task_path), str(target_dir))

    # Update metadata
    meta = read_meta(target_dir)
    meta["status"] = target_status
    if target_status == "complete" and "completed" not in meta:
        meta["completed"] = get_utc_now()
    write_meta(target_dir, meta)

    # Rebuild INDEX.md
    content = build_index(tasks_root)
    (tasks_root / "INDEX.md").write_text(content)

    data = {
        "id": task_id,
        "from_status": current_status,
        "to_status": target_status,
        "changed": True,
        "path": str(target_dir),
    }
    warnings = []
    if meta.get("parent_epic"):
        data["epic_sync_needed"] = meta["parent_epic"]
        warnings.append(f"Run epic-sync for epic #{meta['parent_epic']}")

    output_success("transition", data, warnings=warnings or None)


def cmd_prioritize(args):
    """Set task priority."""
    tasks_root = find_tasks_root()
    repo_root = get_repo_root(tasks_root)
    task_id = args.id
    level = args.level

    _, task_path = find_task(tasks_root, task_id)
    meta = read_meta(task_path)

    if meta.get("parent_epic"):
        error_exit(f"Task #{task_id} inherits priority from its epic. Prioritize the epic instead.")

    old_priority = meta.get("priority")
    meta["priority"] = level
    write_meta(task_path, meta)

    content = build_index(tasks_root)
    (tasks_root / "INDEX.md").write_text(content)

    git_add_and_commit(repo_root, f"Tasks: Prioritize #{task_id} as {level}")
    output_success("prioritize", {
        "id": task_id,
        "old_priority": old_priority,
        "new_priority": level,
    })


def cmd_complete(args):
    """Merge branch, cleanup worktree, transition to complete."""
    tasks_root = find_tasks_root()
    repo_root = get_repo_root(tasks_root)
    task_id = args.id

    current_status, task_path = find_task(tasks_root, task_id)
    meta = read_meta(task_path)

    # Epic completion guard
    if meta.get("type") == "epic":
        all_tasks = collect_all_tasks(tasks_root)
        open_children = []
        for s, tid, m in all_tasks:
            if m.get("parent_epic") == task_id and s not in ("complete", "rejected", "consolidated"):
                open_children.append(tid)
        if open_children:
            error_exit(f"Epic #{task_id} cannot be completed — child tasks {', '.join(f'#{c}' for c in open_children)} are still open.")

    # Handle worktree
    title = meta.get("title", f"task-{task_id}")
    slug = slugify(title)
    branch = f"feature/task-{task_id}-{slug}"
    worktree_path = repo_root / ".worktrees" / f"task-{task_id}"
    merged_branch = None

    if worktree_path.is_dir():
        # Check for uncommitted changes
        status_result = subprocess.run(
            ["git", "-C", str(worktree_path), "status", "--porcelain"],
            capture_output=True, text=True,
        )
        if status_result.stdout.strip():
            error_exit(f"Uncommitted changes in worktree {worktree_path}. Commit or stash before completing.")

        # Get actual branch name from worktree
        branch_result = subprocess.run(
            ["git", "-C", str(worktree_path), "branch", "--show-current"],
            capture_output=True, text=True,
        )
        if branch_result.stdout.strip():
            branch = branch_result.stdout.strip()

        # Merge
        git("checkout", "main", cwd=repo_root)
        git("merge", branch, cwd=repo_root)
        merged_branch = branch

        # Remove worktree
        git("worktree", "remove", str(worktree_path), cwd=repo_root)

        # Delete branch
        subprocess.run(
            ["git", "branch", "-d", branch],
            cwd=repo_root, capture_output=True, text=True,
        )

        # Cleanup if anything remains
        if worktree_path.exists():
            shutil.rmtree(str(worktree_path), ignore_errors=True)

    # Move to complete
    target_dir = tasks_root / STATUS_DIRS["complete"] / str(task_id)
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(task_path), str(target_dir))

    # Update metadata
    meta = read_meta(target_dir)
    meta["status"] = "complete"
    meta["completed"] = get_utc_now()
    write_meta(target_dir, meta)

    # Rebuild INDEX.md
    content = build_index(tasks_root)
    (tasks_root / "INDEX.md").write_text(content)

    git_add_and_commit(repo_root, f"Tasks: Complete #{task_id}")

    data = {
        "id": task_id,
        "from_status": current_status,
        "completed": meta["completed"],
        "merged_branch": merged_branch,
        "path": str(target_dir),
    }
    warnings = []
    if meta.get("parent_epic"):
        data["epic_sync_needed"] = meta["parent_epic"]
        warnings.append(f"Run epic-sync for epic #{meta['parent_epic']}")

    has_revw = (target_dir / "revw.md").is_file()
    has_legacy_changes = (target_dir / "changes.md").is_file()
    if not has_revw and not has_legacy_changes and meta.get("type") != "epic":
        warnings.append("revw.md not found (branch may already be merged)")

    output_success("complete", data, warnings=warnings or None)


def cmd_reject(args):
    """Reject a task."""
    tasks_root = find_tasks_root()
    repo_root = get_repo_root(tasks_root)
    task_id = args.id
    reason = " ".join(args.reason) if args.reason else None

    if not reason:
        error_exit("Rejection reason is required. Usage: tasks-cli reject <id> <reason>")

    current_status, task_path = find_task(tasks_root, task_id)
    meta = read_meta(task_path)

    # Move to rejected
    target_dir = tasks_root / STATUS_DIRS["rejected"] / str(task_id)
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(task_path), str(target_dir))

    # Update metadata
    meta["status"] = "rejected"
    meta["rejected_reason"] = reason
    write_meta(target_dir, meta)

    # Update spec heading if spec.md exists
    spec_path = target_dir / "spec.md"
    if spec_path.is_file():
        spec_text = spec_path.read_text()
        title = meta.get("title", f"Task {task_id}")
        spec_text = re.sub(
            r"^(#\s+.+?)(\s*✓|\s*✗)?\s*$",
            f"# Task {task_id}: {title} ✗",
            spec_text,
            count=1,
            flags=re.MULTILINE,
        )
        spec_path.write_text(spec_text)

    content = build_index(tasks_root)
    (tasks_root / "INDEX.md").write_text(content)

    git_add_and_commit(repo_root, f"Tasks: Reject #{task_id}")

    data = {
        "id": task_id,
        "from_status": current_status,
        "reason": reason,
        "path": str(target_dir),
    }
    warnings = []
    if meta.get("parent_epic"):
        data["epic_sync_needed"] = meta["parent_epic"]
        warnings.append(f"Run epic-sync for epic #{meta['parent_epic']}")

    output_success("reject", data, warnings=warnings or None)


def cmd_consolidate(args):
    """Consolidate one task into another."""
    tasks_root = find_tasks_root()
    repo_root = get_repo_root(tasks_root)
    source_id = args.id
    target_id = args.into

    # Verify both exist
    source_status, source_path = find_task(tasks_root, source_id)
    _, target_path = find_task(tasks_root, target_id)

    source_meta = read_meta(source_path)

    # Move source to consolidated
    target_dir = tasks_root / STATUS_DIRS["consolidated"] / str(source_id)
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source_path), str(target_dir))

    # Update source metadata
    source_meta["status"] = "consolidated"
    source_meta["consolidated_into"] = target_id
    write_meta(target_dir, source_meta)

    # Update spec heading if spec.md exists
    title = source_meta.get("title", f"Task {source_id}")
    spec_path = target_dir / "spec.md"
    if spec_path.is_file():
        spec_text = spec_path.read_text()
        spec_text = re.sub(
            r"^(#\s+.+?)(\s*✓|\s*✗|\s*→.*?)?\s*$",
            f"# Task {source_id}: {title} → consolidated into #{target_id}",
            spec_text,
            count=1,
            flags=re.MULTILINE,
        )
        # Prepend preservation comment
        if "<!-- Original content preserved below -->" not in spec_text:
            spec_text = re.sub(
                r"^(# .+\n)",
                r"\1\n<!-- Original content preserved below -->\n",
                spec_text,
                count=1,
            )
        spec_path.write_text(spec_text)

    content = build_index(tasks_root)
    (tasks_root / "INDEX.md").write_text(content)

    git_add_and_commit(repo_root, f"Tasks: Consolidate #{source_id} into #{target_id}")

    data = {
        "source_id": source_id,
        "target_id": target_id,
        "from_status": source_status,
        "path": str(target_dir),
    }
    warnings = []
    if source_meta.get("parent_epic"):
        data["epic_sync_needed"] = source_meta["parent_epic"]
        warnings.append(f"Run epic-sync for epic #{source_meta['parent_epic']}")

    output_success("consolidate", data, warnings=warnings or None)
