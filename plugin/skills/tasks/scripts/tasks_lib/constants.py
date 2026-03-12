"""Constants for task lifecycle management."""

from __future__ import annotations

STATUS_DIRS = {
    "inbox": "0-inbox",
    "speccing": "1-speccing",
    "planning": "2-planning",
    "plan-review": "3-plan-review",
    "implementing": "4-implementing",
    "reviewing": "5-reviewing",
    "complete": "6-complete",
    "rejected": "7-rejected",
    "consolidated": "8-consolidated",
}

DIR_TO_STATUS = {v: k for k, v in STATUS_DIRS.items()}

# Ordered for INDEX.md rendering
ACTIVE_STATUSES = ["speccing", "planning", "plan-review", "implementing", "reviewing"]
INBOX_PRIORITIES = ["high", "medium", "low"]
ARCHIVE_STATUSES = ["complete", "rejected", "consolidated"]

VALID_PRIORITIES = {"low", "medium", "high", "inherit"}

# Frontmatter field ordering for serialization
FIELD_ORDER = [
    "id", "title", "type", "priority", "status", "parent_epic",
    "created", "completed", "consolidated_into", "rejected_reason",
    "depends_on", "blocks",
]

# Fields that hold lists of integers
INT_LIST_FIELDS = {"depends_on", "blocks"}
# Fields that hold integers
INT_FIELDS = {"id", "parent_epic", "consolidated_into"}
