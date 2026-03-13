"""Add commands: add, add-epic, add-to-epic."""

from __future__ import annotations

from .constants import STATUS_DIRS
from .helpers import (
    ensure_status_dirs,
    find_task,
    find_tasks_root,
    get_next_id,
    get_repo_root,
    get_utc_now,
    git_add_and_commit,
    items_dir,
)
from .index import build_index
from .io import read_meta, read_spec, write_meta, write_spec
from .output import error_exit, output_success


def cmd_add(args):
    """Create a new task in inbox."""
    tasks_root = find_tasks_root()
    repo_root = get_repo_root(tasks_root)
    ensure_status_dirs(tasks_root)

    description = " ".join(args.description)
    task_id = get_next_id(tasks_root)
    task_dir = items_dir(tasks_root) / "0-inbox" / str(task_id)
    task_dir.mkdir(parents=True)

    now = get_utc_now()
    meta = {
        "id": task_id,
        "title": description,
        "status": "inbox",
        "created": now,
        "depends_on": [],
        "blocks": [],
    }
    write_meta(task_dir, meta)

    spec = (
        f"---\ncreated: {now}\n---\n\n"
        f"# Task {task_id}: {description}\n\n"
        f"## Description\n\n{description}\n\n"
        f"## Acceptance Criteria\n\n- [ ] TBD\n"
    )
    write_spec(task_dir, spec)

    content = build_index(tasks_root)
    (tasks_root / "INDEX.md").write_text(content)

    git_add_and_commit(repo_root, f"Tasks: Add #{task_id}")
    output_success("add", {
        "id": task_id,
        "title": description,
        "status": "inbox",
        "path": str(task_dir),
    })


def cmd_add_epic(args):
    """Create a new epic in inbox."""
    tasks_root = find_tasks_root()
    repo_root = get_repo_root(tasks_root)
    ensure_status_dirs(tasks_root)

    description = " ".join(args.description)
    task_id = get_next_id(tasks_root)
    task_dir = items_dir(tasks_root) / "0-inbox" / str(task_id)
    task_dir.mkdir(parents=True)

    now = get_utc_now()
    meta = {
        "id": task_id,
        "title": description,
        "type": "epic",
        "status": "inbox",
        "created": now,
    }
    write_meta(task_dir, meta)

    spec = (
        f"---\ncreated: {now}\n---\n\n"
        f"# {description}\n\n"
        f"## Description\n\n{description}\n\n"
        f"## Motivation\n\nTBD\n\n"
        f"## Scope\n\n### In scope\n\n- TBD\n\n### Out of scope\n\n- TBD\n\n"
        f"## Children\n\n"
        f"| # | Task | Status |\n"
        f"|---|------|--------|\n\n"
        f"## Acceptance Criteria\n\n"
        f"- [ ] All child tasks are complete\n"
        f"- [ ] Integration between children is verified\n"
    )
    write_spec(task_dir, spec)

    content = build_index(tasks_root)
    (tasks_root / "INDEX.md").write_text(content)

    git_add_and_commit(repo_root, f"Tasks: Add #{task_id}")
    output_success("add-epic", {
        "id": task_id,
        "title": description,
        "type": "epic",
        "status": "inbox",
        "path": str(task_dir),
    })


def cmd_add_to_epic(args):
    """Create a child task under an epic."""
    tasks_root = find_tasks_root()
    repo_root = get_repo_root(tasks_root)
    ensure_status_dirs(tasks_root)

    epic_id = args.epic_id
    description = " ".join(args.description)

    # Verify epic exists and is an epic
    _, epic_path = find_task(tasks_root, epic_id)
    epic_meta = read_meta(epic_path)
    if epic_meta.get("type") != "epic":
        error_exit(f"Task #{epic_id} is not an epic.")

    task_id = get_next_id(tasks_root)
    task_dir = items_dir(tasks_root) / "0-inbox" / str(task_id)
    task_dir.mkdir(parents=True)

    now = get_utc_now()
    meta = {
        "id": task_id,
        "title": description,
        "priority": "inherit",
        "status": "inbox",
        "parent_epic": epic_id,
        "created": now,
        "depends_on": [],
        "blocks": [],
    }
    write_meta(task_dir, meta)

    spec = (
        f"---\ncreated: {now}\n---\n\n"
        f"# Task {task_id}: {description}\n\n"
        f"## Description\n\n{description}\n\n"
        f"## Acceptance Criteria\n\n- [ ] TBD\n"
    )
    write_spec(task_dir, spec)

    # Update epic's Children table in spec.md
    epic_spec = read_spec(epic_path)
    epic_spec = _add_child_to_epic_table(epic_spec, task_id, description, "inbox", tasks_root, epic_path)
    write_spec(epic_path, epic_spec)

    content = build_index(tasks_root)
    (tasks_root / "INDEX.md").write_text(content)

    git_add_and_commit(repo_root, f"Tasks: Add #{task_id} to epic #{epic_id}")
    output_success("add-to-epic", {
        "id": task_id,
        "title": description,
        "status": "inbox",
        "parent_epic": epic_id,
        "path": str(task_dir),
    })


def _add_child_to_epic_table(epic_spec: str, child_id: int, title: str,
                              status: str, tasks_root, epic_path) -> str:
    """Add a row to the epic's ## Children table in spec.md."""
    status_dir = STATUS_DIRS[status]
    rel_path = f"../{status_dir}/{child_id}/spec.md"
    new_row = f"| [#{child_id}]({rel_path}) | {title} | {status} |"

    lines = epic_spec.split("\n")
    result = []
    in_children = False
    inserted = False

    for i, line in enumerate(lines):
        if line.strip() == "## Children":
            in_children = True
            result.append(line)
            continue

        if in_children and not inserted:
            if line.startswith("|"):
                result.append(line)
                continue
            elif line.strip() == "" and i > 0 and result and result[-1].startswith("|"):
                result.append(new_row)
                result.append(line)
                inserted = True
                in_children = False
                continue
            elif line.startswith("#"):
                result.append(new_row)
                result.append("")
                result.append(line)
                inserted = True
                in_children = False
                continue
            else:
                result.append(line)
                continue

        result.append(line)

    if in_children and not inserted:
        result.append(new_row)

    return "\n".join(result)
