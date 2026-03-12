"""YAML parsing and serialization for task files."""

from __future__ import annotations

from .constants import FIELD_ORDER, INT_FIELDS, INT_LIST_FIELDS


def parse_yaml(text: str) -> dict:
    """Parse a simple YAML file into a dict.

    Handles scalars, inline lists [a, b], and multi-line lists (- item).
    Sufficient for task.yaml without requiring PyYAML.
    """
    meta = {}
    current_key = None
    current_list = None

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Multi-line list item: "  - value"
        if line.startswith("  - ") and current_key is not None:
            val = line.strip()[2:].strip()
            if current_list is None:
                current_list = []
            current_list.append(_cast_value(current_key, val))
            meta[current_key] = current_list
            continue

        # Key-value pair
        colon_idx = stripped.find(": ")
        if colon_idx == -1 and stripped.endswith(":"):
            # Key with no value (multi-line list follows)
            current_key = stripped[:-1]
            current_list = []
            meta[current_key] = current_list
            continue
        if colon_idx == -1:
            continue

        key = stripped[:colon_idx]
        val_str = stripped[colon_idx + 2:]
        current_key = key
        current_list = None

        # Inline list: [a, b, c]
        if val_str.startswith("[") and val_str.endswith("]"):
            inner = val_str[1:-1].strip()
            if not inner:
                meta[key] = []
            else:
                items = [s.strip() for s in inner.split(",")]
                meta[key] = [_cast_value(key, i) for i in items]
            continue

        # Scalar value
        meta[key] = _cast_value(key, val_str)

    return meta


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown text (for plan.md, revw.md, etc.).

    Returns (frontmatter_dict, body) where body is everything after
    the closing '---'.
    """
    if not text.startswith("---"):
        return {}, text

    end = text.find("\n---", 3)
    if end == -1:
        return {}, text

    yaml_block = text[4:end]  # skip opening ---\n
    body = text[end + 4:]  # skip \n---\n
    if body.startswith("\n"):
        body = body[1:]

    return parse_yaml(yaml_block), body


def _cast_value(key: str, val: str):
    """Cast a string value to the appropriate type based on field name."""
    if key in INT_FIELDS:
        try:
            return int(val)
        except (ValueError, TypeError):
            return val
    if key in INT_LIST_FIELDS:
        try:
            return int(val)
        except (ValueError, TypeError):
            return val
    return val


def serialize_yaml(meta: dict) -> str:
    """Serialize a dict to YAML string (no --- delimiters)."""
    lines = []
    for key in FIELD_ORDER:
        if key not in meta:
            continue
        val = meta[key]
        if val is None:
            continue
        if isinstance(val, list):
            if not val:
                lines.append(f"{key}: []")
            elif key in INT_LIST_FIELDS:
                items = ", ".join(str(v) for v in val)
                lines.append(f"{key}: [{items}]")
            else:
                lines.append(f"{key}:")
                for item in val:
                    lines.append(f"  - {item}")
        elif isinstance(val, int):
            lines.append(f"{key}: {val}")
        else:
            lines.append(f"{key}: {val}")

    # Include any fields not in FIELD_ORDER (preserve unknowns)
    for key in meta:
        if key not in FIELD_ORDER and meta[key] is not None:
            val = meta[key]
            if isinstance(val, list):
                if not val:
                    lines.append(f"{key}: []")
                else:
                    items = ", ".join(str(v) for v in val)
                    lines.append(f"{key}: [{items}]")
            else:
                lines.append(f"{key}: {val}")

    return "\n".join(lines)
