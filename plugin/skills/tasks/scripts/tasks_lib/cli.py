"""Argument parser and command dispatch."""

from __future__ import annotations

import argparse
import sys

from .constants import STATUS_DIRS
from .output import set_current_command

from .cmd_add import cmd_add, cmd_add_epic, cmd_add_to_epic
from .cmd_lifecycle import cmd_complete, cmd_consolidate, cmd_prioritize, cmd_reject, cmd_transition
from .cmd_query import cmd_audit, cmd_epic_sync, cmd_list
from .cmd_review import cmd_review
from .index import cmd_sync_index


def main():
    parser = argparse.ArgumentParser(
        prog="tasks-cli",
        description="Deterministic task lifecycle management CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # add
    p_add = sub.add_parser("add", help="Create task in inbox")
    p_add.add_argument("description", nargs="+")

    # add-epic
    p_epic = sub.add_parser("add-epic", help="Create epic in inbox")
    p_epic.add_argument("description", nargs="+")

    # add-to-epic
    p_ate = sub.add_parser("add-to-epic", help="Add child task to epic")
    p_ate.add_argument("epic_id", type=int)
    p_ate.add_argument("description", nargs="+")

    # transition
    p_tr = sub.add_parser("transition", help="Move task to new status")
    p_tr.add_argument("id", type=int)
    p_tr.add_argument("status", choices=list(STATUS_DIRS.keys()))

    # prioritize
    p_pr = sub.add_parser("prioritize", help="Set task priority")
    p_pr.add_argument("id", type=int)
    p_pr.add_argument("level", choices=["low", "medium", "high"])

    # list
    p_ls = sub.add_parser("list", help="Show backlog table")
    p_ls.add_argument("--all", action="store_true", help="Include archived tasks")

    # sync-index
    sub.add_parser("sync-index", help="Rebuild INDEX.md from filesystem")

    # review
    p_rv = sub.add_parser("review", help="Generate revw.md from git diff")
    p_rv.add_argument("id", type=int)

    # complete
    p_cp = sub.add_parser("complete", help="Merge branch, cleanup, transition to complete")
    p_cp.add_argument("id", type=int)

    # audit
    sub.add_parser("audit", help="Run structural checks")

    # epic-sync
    p_es = sub.add_parser("epic-sync", help="Sync epic children table")
    p_es.add_argument("epic_id", type=int)

    # reject
    p_rj = sub.add_parser("reject", help="Reject a task")
    p_rj.add_argument("id", type=int)
    p_rj.add_argument("reason", nargs="*")

    # consolidate
    p_co = sub.add_parser("consolidate", help="Consolidate task into another")
    p_co.add_argument("id", type=int)
    p_co.add_argument("into", type=int, help="Target task ID")

    args = parser.parse_args()

    set_current_command(args.command)

    dispatch = {
        "add": cmd_add,
        "add-epic": cmd_add_epic,
        "add-to-epic": cmd_add_to_epic,
        "transition": cmd_transition,
        "prioritize": cmd_prioritize,
        "list": cmd_list,
        "sync-index": cmd_sync_index,
        "review": cmd_review,
        "complete": cmd_complete,
        "audit": cmd_audit,
        "epic-sync": cmd_epic_sync,
        "reject": cmd_reject,
        "consolidate": cmd_consolidate,
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)
