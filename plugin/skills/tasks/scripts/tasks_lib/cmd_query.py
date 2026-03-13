"""Query commands: list, audit, epic-sync."""

from __future__ import annotations

import re

from .constants import (
    ACTIVE_STATUSES,
    ARCHIVE_STATUSES,
    STATUS_DIRS,
    VALID_PRIORITIES,
)
from .helpers import (
    collect_all_tasks,
    find_task,
    find_tasks_root,
    get_effective_priority,
    items_dir,
)
from .io import read_meta, read_spec, write_spec
from .output import error_exit, output_success


def cmd_list(args):
    """Display backlog as structured JSON."""
    tasks_root = find_tasks_root()
    all_tasks = collect_all_tasks(tasks_root)
    show_all = getattr(args, "all", False)

    tasks_out = []
    for status, tid, meta in all_tasks:
        if not show_all and status in ARCHIVE_STATUSES:
            continue
        tasks_out.append({
            "id": tid,
            "title": meta.get("title", f"Task {tid}"),
            "type": meta.get("type", "change"),
            "status": status,
            "priority": get_effective_priority(meta, tasks_root),
            "parent_epic": meta.get("parent_epic"),
            "created": meta.get("created"),
        })

    # Sort: active first, then inbox by priority, then by ID desc
    status_order = {s: i for i, s in enumerate(ACTIVE_STATUSES + ["inbox"] + ARCHIVE_STATUSES)}
    priority_order = {"high": 0, "medium": 1, "low": 2, None: 3}

    tasks_out.sort(key=lambda t: (
        status_order.get(t["status"], 99),
        priority_order.get(t["priority"], 99),
        -t["id"],
    ))

    # Summary counts
    counts_by_status = {}
    for t in tasks_out:
        counts_by_status[t["status"]] = counts_by_status.get(t["status"], 0) + 1
    open_count = sum(v for k, v in counts_by_status.items() if k not in ARCHIVE_STATUSES)
    inbox_by_priority = {}
    for t in tasks_out:
        if t["status"] == "inbox" and t["priority"]:
            inbox_by_priority[t["priority"]] = inbox_by_priority.get(t["priority"], 0) + 1

    output_success("list", {
        "tasks": tasks_out,
        "summary": {
            "open": open_count,
            "by_status": counts_by_status,
            "inbox_by_priority": inbox_by_priority,
        },
    })


def cmd_audit(args):
    """Run structural and consistency checks on the backlog."""
    tasks_root = find_tasks_root()
    all_tasks = collect_all_tasks(tasks_root)

    errors = []
    warnings = []

    task_ids = {tid for _, tid, _ in all_tasks}
    task_map = {tid: (s, m) for s, tid, m in all_tasks}

    # --- Check 1: Structural Integrity ---
    for status_dir_name in STATUS_DIRS.values():
        dir_path = items_dir(tasks_root) / status_dir_name
        if not dir_path.is_dir():
            continue
        for entry in dir_path.iterdir():
            if entry.name == ".gitkeep":
                continue
            if not entry.is_dir():
                warnings.append(f"Unexpected file in {status_dir_name}/: {entry.name}")
                continue
            try:
                int(entry.name)
            except ValueError:
                errors.append(f"Non-numeric folder in {status_dir_name}/: {entry.name}")
                continue
            has_yaml = (entry / "task.yaml").is_file()
            has_legacy = (entry / "task.md").is_file()
            if not has_yaml and not has_legacy:
                errors.append(f"Missing task.yaml in {status_dir_name}/{entry.name}/")
            elif has_legacy and not has_yaml:
                warnings.append(f"Legacy task.md in {status_dir_name}/{entry.name}/ — consider migrating to task.yaml + spec.md")

    # --- Check 2: Frontmatter Compliance ---
    for status, tid, meta in all_tasks:
        prefix = f"#{tid}"

        for field in ("id", "title", "status", "created"):
            if field not in meta:
                errors.append(f"{prefix}: Missing required field '{field}'")

        if meta.get("id") != tid:
            errors.append(f"{prefix}: Metadata id={meta.get('id')} doesn't match folder name {tid}")

        if meta.get("status") != status:
            errors.append(f"{prefix}: Metadata status='{meta.get('status')}' but task is in {STATUS_DIRS[status]}/")

        if status == "rejected" and not meta.get("rejected_reason"):
            warnings.append(f"{prefix}: Rejected without 'rejected_reason'")
        if status == "consolidated" and not meta.get("consolidated_into"):
            warnings.append(f"{prefix}: Consolidated without 'consolidated_into'")
        if status == "complete" and not meta.get("completed"):
            warnings.append(f"{prefix}: Complete without 'completed' datetime")

        pri = meta.get("priority")
        if pri is not None and pri not in VALID_PRIORITIES:
            errors.append(f"{prefix}: Invalid priority '{pri}'")
        if pri == "inherit" and not meta.get("parent_epic"):
            errors.append(f"{prefix}: priority='inherit' but no parent_epic set")

        for dep_field in ("depends_on", "blocks"):
            deps = meta.get(dep_field, [])
            if isinstance(deps, list):
                for dep_id in deps:
                    if isinstance(dep_id, int) and dep_id not in task_ids:
                        errors.append(f"{prefix}: {dep_field} references non-existent #{dep_id}")

    # --- Check 3: INDEX.md Sync ---
    index_path = tasks_root / "INDEX.md"
    if index_path.is_file():
        index_text = index_path.read_text()
        index_ids = set()
        for match in re.finditer(r"\[#(\d+)\]", index_text):
            index_ids.add(int(match.group(1)))

        for status, tid, meta in all_tasks:
            if status not in ARCHIVE_STATUSES and tid not in index_ids:
                errors.append(f"#{tid}: Active task not in INDEX.md")

        for idx_id in index_ids:
            if idx_id not in task_ids:
                errors.append(f"INDEX.md references #{idx_id} but no task folder exists")
    else:
        errors.append("INDEX.md not found")

    # --- Check 4: Spec heading consistency ---
    for status, tid, meta in all_tasks:
        task_dir = items_dir(tasks_root) / STATUS_DIRS[status] / str(tid)
        spec_text = read_spec(task_dir)
        if spec_text:
            title = meta.get("title", "")
            heading_match = re.search(r"^#\s+(.+)$", spec_text, re.MULTILINE)
            if heading_match:
                heading = heading_match.group(1).strip()
                clean_heading = re.sub(r"\s*[✓✗].*$", "", heading)
                clean_heading = re.sub(r"\s*→\s*consolidated.*$", "", clean_heading)
                clean_heading = re.sub(r"^Task\s+\d+:\s*", "", clean_heading)
                if clean_heading != title and clean_heading.strip() != title.strip():
                    warnings.append(f"#{tid}: Title mismatch — metadata='{title}', heading='{clean_heading}'")

    # --- Check 5: Dependency Integrity ---
    dep_graph = {}
    for _, tid, meta in all_tasks:
        deps = meta.get("depends_on", [])
        if isinstance(deps, list):
            dep_graph[tid] = [d for d in deps if isinstance(d, int)]
        else:
            dep_graph[tid] = []

    for _, tid, meta in all_tasks:
        for dep_id in dep_graph.get(tid, []):
            if dep_id in task_map:
                dep_status, _ = task_map[dep_id]
                if dep_status in ("rejected", "consolidated"):
                    warnings.append(f"#{tid}: depends_on #{dep_id} which is {dep_status}")

    for _, tid, meta in all_tasks:
        blocks = meta.get("blocks", [])
        if isinstance(blocks, list):
            for blocked_id in blocks:
                if isinstance(blocked_id, int) and blocked_id in task_map:
                    _, blocked_meta = task_map[blocked_id]
                    blocked_deps = blocked_meta.get("depends_on", [])
                    if not isinstance(blocked_deps, list) or tid not in blocked_deps:
                        warnings.append(f"#{tid} blocks #{blocked_id}, but #{blocked_id} doesn't depend on #{tid}")

    def has_cycle(start, visited=None, path=None):
        if visited is None:
            visited = set()
        if path is None:
            path = set()
        visited.add(start)
        path.add(start)
        for dep in dep_graph.get(start, []):
            if dep in path:
                return True
            if dep not in visited and has_cycle(dep, visited, path):
                return True
        path.discard(start)
        return False

    visited_global = set()
    for tid in dep_graph:
        if tid not in visited_global:
            if has_cycle(tid, visited_global):
                errors.append(f"Circular dependency detected involving #{tid}")

    # --- Summary ---
    status_counts = {}
    for status, _, _ in all_tasks:
        status_counts[status] = status_counts.get(status, 0) + 1
    open_count = sum(v for k, v in status_counts.items() if k not in ARCHIVE_STATUSES)

    oldest = None
    for status, tid, meta in all_tasks:
        if status not in ARCHIVE_STATUSES:
            created = meta.get("created", "")
            if oldest is None or created < oldest[1]:
                oldest = (tid, created)

    output_success("audit", {
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "total_tasks": len(all_tasks),
            "open_tasks": open_count,
            "by_status": status_counts,
            "oldest_open": {"id": oldest[0], "created": oldest[1]} if oldest else None,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "passed": len(errors) == 0 and len(warnings) == 0,
        },
    })


def cmd_epic_sync(args):
    """Sync epic's Children table from filesystem state."""
    tasks_root = find_tasks_root()
    epic_id = args.epic_id

    _, epic_path = find_task(tasks_root, epic_id)
    epic_meta = read_meta(epic_path)

    if epic_meta.get("type") != "epic":
        error_exit(f"Task #{epic_id} is not an epic.")

    # Find all children
    all_tasks = collect_all_tasks(tasks_root)
    children = []
    for status, tid, meta in all_tasks:
        if meta.get("parent_epic") == epic_id:
            children.append((tid, meta.get("title", f"Task {tid}"), status))

    children.sort(key=lambda x: x[0])

    # Build new table
    table_lines = [
        "| # | Task | Status |",
        "|---|------|--------|",
    ]
    for tid, title, status in children:
        child_dir = STATUS_DIRS[status]
        rel_path = f"../{child_dir}/{tid}/spec.md"
        table_lines.append(f"| [#{tid}]({rel_path}) | {title} | {status} |")

    new_table = "\n".join(table_lines)

    # Replace the Children table in spec.md
    epic_spec = read_spec(epic_path)
    lines = epic_spec.split("\n")
    result = []
    in_children = False
    table_replaced = False

    for line in lines:
        if line.strip() == "## Children":
            in_children = True
            result.append(line)
            result.append("")
            result.append(new_table)
            table_replaced = True
            continue

        if in_children:
            if line.startswith("## ") and line.strip() != "## Children":
                in_children = False
                result.append("")
                result.append(line)
            continue

        result.append(line)

    if not table_replaced:
        result.append("\n## Children\n")
        result.append(new_table)

    epic_spec = "\n".join(result)
    write_spec(epic_path, epic_spec)

    output_success("epic-sync", {
        "epic_id": epic_id,
        "children_count": len(children),
        "children": [{"id": tid, "title": title, "status": status} for tid, title, status in children],
    })
