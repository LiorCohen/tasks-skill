"""Review command: generate revw.md from git diff."""

from __future__ import annotations

import re
import subprocess

from .helpers import find_task, find_tasks_root, get_repo_root, get_utc_now, slugify
from .io import read_meta
from .output import output_success


def cmd_review(args):
    """Generate revw.md from git diff."""
    tasks_root = find_tasks_root()
    repo_root = get_repo_root(tasks_root)
    task_id = args.id

    _, task_path = find_task(tasks_root, task_id)
    meta = read_meta(task_path)

    title = meta.get("title", f"task-{task_id}")
    slug = slugify(title)
    branch = f"feature/task-{task_id}-{slug}"

    # Check if worktree exists
    worktree_path = repo_root / ".worktrees" / f"task-{task_id}"
    if worktree_path.is_dir():
        # Read actual branch name from worktree
        branch_result = subprocess.run(
            ["git", "-C", str(worktree_path), "branch", "--show-current"],
            capture_output=True, text=True,
        )
        if branch_result.stdout.strip():
            branch = branch_result.stdout.strip()
        diff_cwd = str(worktree_path)
        diff_ref = "main..HEAD"
    else:
        diff_cwd = str(repo_root)
        diff_ref = f"main..{branch}"

    # Get commit count
    log_result = subprocess.run(
        ["git", "log", "--oneline", diff_ref],
        cwd=diff_cwd, capture_output=True, text=True,
    )
    commit_count = len(log_result.stdout.strip().split("\n")) if log_result.stdout.strip() else 0

    # Count iterations from impl.md if it exists
    impl_path = task_path / "impl.md"
    iteration_count = 0
    if impl_path.is_file():
        impl_text = impl_path.read_text()
        iteration_count = len(re.findall(r"^## Iteration \d+", impl_text, re.MULTILINE))

    # Get numstat
    numstat_result = subprocess.run(
        ["git", "diff", diff_ref, "--numstat", "--", ":!.tasks/"],
        cwd=diff_cwd, capture_output=True, text=True,
    )

    files = []
    total_added = 0
    total_removed = 0

    for line in numstat_result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, removed, filepath = parts
        try:
            a = int(added)
            r = int(removed)
        except ValueError:
            a, r = 0, 0
        files.append({"file": filepath, "added": a, "removed": r})
        total_added += a
        total_removed += r

    now = get_utc_now()

    # Build revw.md
    md_lines = [
        "---",
        f"generated: {now}",
        f"branch: {branch}",
        f"commits: {commit_count}",
        f"iterations: {iteration_count}",
        "---",
        "",
        f"# Review: Task #{task_id}",
        "",
        "## Summary",
        "",
        f"**Files changed:** {len(files)} (+{total_added} / -{total_removed} lines)",
        f"**Iterations:** {iteration_count}",
        "",
        "| File | Added | Removed |",
        "|------|------:|--------:|",
    ]

    for f in files:
        md_lines.append(f"| [`{f['file']}`]({f['file']}) | +{f['added']} | -{f['removed']} |")

    md_lines.extend([
        "",
        "## Acceptance Criteria — Final",
        "",
        "_(Populated from spec.md during review)_",
        "",
        "## Review Notes",
        "",
        "_(Filled during review phase)_",
    ])

    revw_content = "\n".join(md_lines) + "\n"
    revw_path = task_path / "revw.md"
    revw_path.write_text(revw_content)

    output_success("review", {
        "id": task_id,
        "branch": branch,
        "commits": commit_count,
        "iterations": iteration_count,
        "files_changed": len(files),
        "total_added": total_added,
        "total_removed": total_removed,
        "files": files,
        "revw_path": str(revw_path),
    })
