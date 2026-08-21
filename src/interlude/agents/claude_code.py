"""Claude Code host adapter.

Claude Code:
  * Passes hook context to scripts as a JSON object on stdin. Field of interest
    here: `session_id`.
  * Reads a JSON object back from stdout. Emitting `{}` is the safest 'no-op'
    response; it never becomes conversation.
  * Configures the status line via `~/.claude/settings.json`'s `statusLine`
    entry, which points at a shell command. Interlude installs its shell
    wrapper there.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from ..config import STATUSLINE_MARKER, WRAPPER_SCRIPT
from ..io_utils import read_json
from .base import AgentAdapter


class ClaudeCodeAdapter(AgentAdapter):
    name = "claude-code"

    # --- hook I/O ----------------------------------------------------------

    def read_hook_payload(self) -> dict[str, Any]:
        raw = sys.stdin.read()
        if not raw.strip():
            return {}
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def session_id_of(self, payload: dict[str, Any]) -> str:
        return str(payload.get("session_id") or "default")

    def emit_hook_ok(self) -> None:
        sys.stdout.write("{}\n")
        sys.stdout.flush()

    # --- status line -------------------------------------------------------

    def supports_statusline(self) -> bool:
        return True

    def is_our_statusline(self, command: Any) -> bool:
        if not isinstance(command, str):
            return False
        looks_like_ours = "interlude.sh" in command or "interlude.py" in command
        return STATUSLINE_MARKER in command or (looks_like_ours and "statusline" in command)

    def install_statusline(self, *, if_missing: bool, force: bool, silent: bool) -> str:
        path = _settings_path()
        settings = _load_settings(path)
        existing = settings.get("statusLine")
        existing_cmd = existing.get("command") if isinstance(existing, dict) else None

        if existing and not self.is_our_statusline(existing_cmd) and not force:
            if not silent:
                print(
                    "A custom statusLine is already configured; leaving it unchanged. "
                    "Re-run with --force to replace it.",
                    file=sys.stderr,
                )
            return "skipped"

        if if_missing and existing and self.is_our_statusline(existing_cmd):
            settings["statusLine"] = _statusline_block()
            _save_settings(path, settings)
            return "updated"

        if if_missing and existing:
            return "skipped"

        settings["statusLine"] = _statusline_block()
        _save_settings(path, settings)
        if not silent:
            print(f"Installed Interlude status line in {path}")
        return "installed"

    def uninstall_statusline(self) -> None:
        path = _settings_path()
        settings = _load_settings(path)
        existing = settings.get("statusLine")
        command = existing.get("command") if isinstance(existing, dict) else None
        if not self.is_our_statusline(command):
            print("No Interlude status line is installed.")
            return
        settings.pop("statusLine", None)
        _save_settings(path, settings)
        print(f"Removed Interlude status line from {path}")


# --- settings I/O -----------------------------------------------------------

def _settings_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


def _load_settings(path: Path) -> dict[str, Any]:
    data = read_json(path)
    return data if isinstance(data, dict) else {}


def _save_settings(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_suffix(".json.interlude.bak")
        if not backup.exists():
            backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def _statusline_block() -> dict[str, Any]:
    command = f'sh "{WRAPPER_SCRIPT}" statusline # {STATUSLINE_MARKER}'
    return {"type": "command", "command": command, "refreshInterval": 1}
