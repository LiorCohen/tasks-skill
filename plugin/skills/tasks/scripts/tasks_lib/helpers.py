"""Core helpers for task filesystem operations."""

from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .constants import STATUS_DIRS
from .io import read_meta
from .output import error_exit


def find_tasks_root() -> Path:
    """Walk up from cwd looking for .tasks/ directory."""
    current = Path.cwd()
    while True:
        candidate = current / ".tasks"
        if candidate.is_dir():
            return candidate
        parent = current.parent
        if parent == current:
            break
        current = parent
    error_exit(".tasks/ directory not found. Are you in a project with tasks?")


def get_repo_root(tasks_root: Path) -> Path:
    """Get the repository root (parent of .tasks/)."""
    return tasks_root.parent


def get_next_id(tasks_root: Path) -> int:
    """Scan all status dirs, find highest numeric folder name, return +1."""
    max_id = 0
    for status_dir in STATUS_DIRS.values():
        dir_path = tasks_root / status_dir
        if not dir_path.is_dir():
            continue
        for entry in dir_path.iterdir():
            if entry.is_dir():
                try:
                    task_id = int(entry.name)
                    max_id = max(max_id, task_id)
                except ValueError:
                    pass
    return max_id + 1


def find_task(tasks_root: Path, task_id: int) -> tuple[str, Path]:
    """Find which status dir contains task_id.

    Returns (status_name, full_path_to_task_folder).
    """
    for status_dir_name, dir_name in STATUS_DIRS.items():
        task_path = tasks_root / dir_name / str(task_id)
        if task_path.is_dir():
            return status_dir_name, task_path
    error_exit(f"Task #{task_id} not found in any status directory.")


def slugify(title: str, max_len: int = 40) -> str:
    """Convert title to URL-safe slug for branch names."""
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug[:max_len].rstrip("-")


def get_utc_now() -> str:
    """Return current UTC time as 'YYYY-MM-DD HH:MM UTC'."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%d %H:%M UTC")


def git(*args, cwd=None) -> subprocess.CompletedProcess:
    """Run a git command, raising on failure."""
    result = subprocess.run(
        ["git"] + list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        error_exit(f"git {' '.join(args)} failed:\n{result.stderr.strip()}")
    return result


def git_add_and_commit(repo_root: Path, message: str):
    """Stage .tasks/ changes and commit."""
    git("add", ".tasks/", cwd=repo_root)
    # Check if there's anything to commit
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=repo_root,
        capture_output=True,
    )
    if result.returncode == 0:
        # Nothing staged
        return
    git("commit", "-m", message, cwd=repo_root)


def ensure_status_dirs(tasks_root: Path):
    """Ensure all status directories exist."""
    for dir_name in STATUS_DIRS.values():
        (tasks_root / dir_name).mkdir(parents=True, exist_ok=True)


def collect_all_tasks(tasks_root: Path) -> list[tuple[str, int, dict]]:
    """Scan all status dirs and return list of (status, id, meta)."""
    tasks = []
    for status_name, dir_name in STATUS_DIRS.items():
        dir_path = tasks_root / dir_name
        if not dir_path.is_dir():
            continue
        for entry in sorted(dir_path.iterdir()):
            if not entry.is_dir():
                continue
            try:
                task_id = int(entry.name)
            except ValueError:
                continue
            # Read metadata from task.yaml (with legacy task.md fallback)
            meta = read_meta(entry)
            tasks.append((status_name, task_id, meta))
    return tasks


def get_effective_priority(meta: dict, tasks_root: Path) -> str | None:
    """Get effective priority, resolving 'inherit' from parent epic."""
    priority = meta.get("priority")
    if priority == "inherit" and "parent_epic" in meta:
        parent_id = meta["parent_epic"]
        try:
            _, parent_path = find_task(tasks_root, int(parent_id))
            parent_meta = read_meta(parent_path)
            return parent_meta.get("priority")
        except SystemExit:
            return None
    return priority
