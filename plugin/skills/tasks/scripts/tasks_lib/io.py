"""File I/O helpers for task metadata and spec files."""

from __future__ import annotations

from pathlib import Path

from .output import error_exit
from .parsing import parse_frontmatter, parse_yaml, serialize_yaml


def read_meta(task_dir: str | Path) -> dict:
    """Read task.yaml from a task directory. Returns metadata dict."""
    yaml_path = Path(task_dir) / "task.yaml"
    if not yaml_path.is_file():
        # Fallback: try legacy task.md with frontmatter
        md_path = Path(task_dir) / "task.md"
        if md_path.is_file():
            text = md_path.read_text()
            meta, _ = parse_frontmatter(text)
            return meta
        error_exit(f"No task.yaml found in {task_dir}")
    return parse_yaml(yaml_path.read_text())


def write_meta(task_dir: str | Path, meta: dict):
    """Write metadata to task.yaml in a task directory."""
    yaml_path = Path(task_dir) / "task.yaml"
    yaml_path.write_text(serialize_yaml(meta) + "\n")


def read_spec(task_dir: str | Path) -> str:
    """Read spec.md from a task directory. Returns content or empty string."""
    spec_path = Path(task_dir) / "spec.md"
    if spec_path.is_file():
        return spec_path.read_text()
    # Fallback: try legacy task.md body
    md_path = Path(task_dir) / "task.md"
    if md_path.is_file():
        text = md_path.read_text()
        _, body = parse_frontmatter(text)
        return body
    return ""


def write_spec(task_dir: str | Path, content: str):
    """Write spec.md in a task directory."""
    spec_path = Path(task_dir) / "spec.md"
    spec_path.write_text(content)
