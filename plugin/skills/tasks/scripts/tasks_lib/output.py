"""JSON output helpers for structured CLI responses."""

from __future__ import annotations

import json
import sys

# Global to track current command name for error_exit
_current_command = "unknown"


def set_current_command(name: str):
    """Set the current command name for error messages."""
    global _current_command
    _current_command = name


def output_success(command: str, data: dict, warnings: list[str] | None = None):
    """Print structured JSON result to stdout and exit 0."""
    result = {"ok": True, "command": command, "data": data}
    if warnings:
        result["warnings"] = warnings
    print(json.dumps(result, indent=2))


def output_error(command: str, message: str):
    """Print structured JSON error to stderr and exit 1."""
    result = {"ok": False, "command": command, "error": message}
    print(json.dumps(result, indent=2), file=sys.stderr)
    sys.exit(1)


def error_exit(msg: str):
    """Print JSON error to stderr and exit."""
    output_error(_current_command, msg)
