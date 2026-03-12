"""Viewer commands: install-viewer, uninstall-viewer."""

from __future__ import annotations

import glob
import os
import subprocess
from pathlib import Path

from .output import error_exit, output_success


def _get_viewer_dir() -> Path:
    """Get the viewer source directory relative to this script."""
    # scripts/tasks_lib/cmd_viewer.py -> scripts/ -> viewer/
    return Path(__file__).resolve().parent.parent.parent / "viewer"


def cmd_install_viewer(args):
    """Build and install the Tasks Viewer VS Code extension."""
    viewer_dir = _get_viewer_dir()
    install_script = viewer_dir / "install.sh"

    if not install_script.is_file():
        error_exit(f"install.sh not found at {install_script}")

    result = subprocess.run(
        ["bash", str(install_script)],
        cwd=str(viewer_dir),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        error_exit(f"install.sh failed:\n{result.stderr.strip()}")

    # Read installed version from package.json
    pkg_path = viewer_dir / "package.json"
    version = "unknown"
    if pkg_path.is_file():
        import json
        pkg = json.loads(pkg_path.read_text())
        version = pkg.get("version", "unknown")

    output_success("install-viewer", {
        "version": version,
        "viewer_dir": str(viewer_dir),
        "output": result.stdout.strip(),
    })


def cmd_uninstall_viewer(args):
    """Remove the Tasks Viewer VS Code extension."""
    ext_pattern = os.path.expanduser("~/.vscode/extensions/local.tasks-viewer-*")
    matches = glob.glob(ext_pattern)

    if not matches:
        output_success("uninstall-viewer", {
            "removed": [],
            "message": "No tasks-viewer extension found.",
        })
        return

    import shutil
    removed = []
    for ext_dir in matches:
        shutil.rmtree(ext_dir, ignore_errors=True)
        removed.append(ext_dir)

    output_success("uninstall-viewer", {
        "removed": removed,
        "message": f"Removed {len(removed)} extension(s). Reload VS Code to apply.",
    })
