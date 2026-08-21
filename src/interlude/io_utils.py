"""Small filesystem helpers used across modules."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def atomic_write_json(path: Path, data: Any) -> None:
    """Write JSON via a temporary file then rename, so readers never see a partial write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path) -> Any | None:
    """Return parsed JSON, or None if the file is missing or unreadable."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
