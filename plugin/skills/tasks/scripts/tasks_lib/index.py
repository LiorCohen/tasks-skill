"""INDEX.md building and sync command."""

from __future__ import annotations

from pathlib import Path

from .constants import ACTIVE_STATUSES, ARCHIVE_STATUSES, INBOX_PRIORITIES, ITEMS_SUBDIR, STATUS_DIRS
from .helpers import collect_all_tasks, find_tasks_root, get_effective_priority, items_dir
from .output import output_success


def build_index(tasks_root: Path) -> str:
    """Build INDEX.md content from filesystem state."""
    all_tasks = collect_all_tasks(tasks_root)

    sections = []
    sections.append("# Tasks Backlog")

    # Active statuses
    for status in ACTIVE_STATUSES:
        status_tasks = [(tid, m) for s, tid, m in all_tasks if s == status]
        if not status_tasks:
            continue
        status_tasks.sort(key=lambda x: x[0], reverse=True)
        label = status.replace("-", " ").title()
        sections.append(f"\n---\n\n## {label}\n")
        for tid, meta in status_tasks:
            title = meta.get("title", f"Task {tid}")
            dir_name = STATUS_DIRS[status]
            # Planning tasks link to plan.md if it exists
            plan_path = items_dir(tasks_root) / dir_name / str(tid) / "plan.md"
            if status in ("planning", "plan-review") and plan_path.is_file():
                sections.append(f"- [#{tid}]({ITEMS_SUBDIR}/{dir_name}/{tid}/plan.md): {title}")
            else:
                sections.append(f"- [#{tid}]({ITEMS_SUBDIR}/{dir_name}/{tid}/): {title}")

    # Inbox grouped by priority
    inbox_tasks = [(tid, m) for s, tid, m in all_tasks if s == "inbox"]
    if inbox_tasks:
        sections.append("\n---\n\n## Inbox\n")

        # Group by effective priority
        by_priority = {"high": [], "medium": [], "low": [], None: []}
        for tid, meta in inbox_tasks:
            eff_pri = get_effective_priority(meta, tasks_root)
            if eff_pri in by_priority:
                by_priority[eff_pri].append((tid, meta))
            else:
                by_priority[None].append((tid, meta))

        for pri in INBOX_PRIORITIES:
            pri_tasks = by_priority.get(pri, [])
            if not pri_tasks:
                continue
            pri_tasks.sort(key=lambda x: x[0], reverse=True)
            sections.append(f"### {pri.title()} Priority\n")
            for tid, meta in pri_tasks:
                title = meta.get("title", f"Task {tid}")
                sections.append(f"- [#{tid}]({ITEMS_SUBDIR}/0-inbox/{tid}/): {title}")
            sections.append("")

        unpri = by_priority.get(None, [])
        if unpri:
            unpri.sort(key=lambda x: x[0], reverse=True)
            sections.append("### Unprioritized\n")
            for tid, meta in unpri:
                title = meta.get("title", f"Task {tid}")
                sections.append(f"- [#{tid}]({ITEMS_SUBDIR}/0-inbox/{tid}/): {title}")
            sections.append("")

    # Archive statuses
    for status in ARCHIVE_STATUSES:
        status_tasks = [(tid, m) for s, tid, m in all_tasks if s == status]
        if not status_tasks:
            continue
        status_tasks.sort(key=lambda x: x[0], reverse=True)
        label = status.title()
        sections.append(f"\n---\n\n## {label}\n")
        for tid, meta in status_tasks:
            title = meta.get("title", f"Task {tid}")
            dir_name = STATUS_DIRS[status]
            if status == "complete":
                completed = meta.get("completed", "")
                date_part = completed.split(" ")[0] if completed else ""
                suffix = f" ✓ ({date_part})" if date_part else " ✓"
                sections.append(f"- [#{tid}]({ITEMS_SUBDIR}/{dir_name}/{tid}/): {title}{suffix}")
            elif status == "rejected":
                reason = meta.get("rejected_reason", "")
                suffix = f" — {reason}" if reason else ""
                sections.append(f"- [#{tid}]({ITEMS_SUBDIR}/{dir_name}/{tid}/): {title}{suffix}")
            elif status == "consolidated":
                target = meta.get("consolidated_into", "?")
                sections.append(f"- [#{tid}]({ITEMS_SUBDIR}/{dir_name}/{tid}/) → #{target}")
            else:
                sections.append(f"- [#{tid}]({ITEMS_SUBDIR}/{dir_name}/{tid}/): {title}")

    return "\n".join(sections) + "\n"


def cmd_sync_index(args):
    """Rebuild INDEX.md from filesystem state."""
    tasks_root = find_tasks_root()
    content = build_index(tasks_root)
    (tasks_root / "INDEX.md").write_text(content)
    all_tasks = collect_all_tasks(tasks_root)
    output_success("sync-index", {
        "tasks_indexed": len(all_tasks),
    })
