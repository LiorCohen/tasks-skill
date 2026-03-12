#!/usr/bin/env python3
"""Deterministic CLI for task lifecycle management.

Thin entry point — all logic lives in tasks_lib/.
"""

from tasks_lib.cli import main

if __name__ == "__main__":
    main()
