"""Migrate command: move legacy layout into items/ subdirectory."""

from __future__ import annotations

import shutil

from .constants import STATUS_DIRS
from .helpers import (
    find_tasks_root,
    get_repo_root,
    git_add_and_commit,
    has_legacy_layout,
    items_dir,
)
from .index import build_index
from .output import error_exit, output_success


def cmd_migrate(args):
    """Move status dirs from .tasks/<status>/ to .tasks/items/<status>/."""
    tasks_root = find_tasks_root()

    if not has_legacy_layout(tasks_root):
        error_exit("No legacy layout detected. Status dirs are already under items/.")

    items = items_dir(tasks_root)
    items.mkdir(exist_ok=True)

    moved = []
    for dir_name in STATUS_DIRS.values():
        src = tasks_root / dir_name
        dst = items / dir_name
        if not src.is_dir():
            continue
        if dst.is_dir():
            # Merge: move individual task folders from src into existing dst
            for entry in src.iterdir():
                entry_dst = dst / entry.name
                if entry_dst.exists():
                    error_exit(
                        f"Conflict: {dir_name}/{entry.name} exists in both "
                        f"legacy and items/ locations. Resolve manually."
                    )
                shutil.move(str(entry), str(entry_dst))
            src.rmdir()
        else:
            shutil.move(str(src), str(dst))
        moved.append(dir_name)

    if not moved:
        error_exit("No status directories found to migrate.")

    # Rebuild INDEX.md with updated paths
    content = build_index(tasks_root)
    (tasks_root / "INDEX.md").write_text(content)

    # Commit the migration
    repo_root = get_repo_root(tasks_root)
    git_add_and_commit(repo_root, "Tasks: Migrate legacy layout to items/ subdirectory")

    output_success("migrate", {
        "migrated_dirs": moved,
        "count": len(moved),
    })
