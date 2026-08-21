"""Adapter selection.

Each host (Claude Code, Cursor, Copilot, ...) is one module here. To add a
new host: implement `AgentAdapter` in a new module and register it in the
`_ADAPTERS` mapping and `_detect` below.
"""

from __future__ import annotations

import os

from .base import AgentAdapter
from .claude_code import ClaudeCodeAdapter

_ADAPTERS: dict[str, type[AgentAdapter]] = {
    ClaudeCodeAdapter.name: ClaudeCodeAdapter,
    # Future: "cursor": CursorAdapter, "copilot": CopilotAdapter, ...
}


def get_adapter(explicit: str | None = None) -> AgentAdapter:
    """Return the adapter for the current host. Detects automatically, but
    respects an explicit override (e.g. `--agent claude-code`).
    """
    name = explicit or _detect()
    cls = _ADAPTERS.get(name) or ClaudeCodeAdapter
    return cls()


def _detect() -> str:
    if os.environ.get("CLAUDE_PLUGIN_ROOT"):
        return "claude-code"
    # Placeholder detection hooks for future adapters:
    #   if os.environ.get("CURSOR_HOOK_ROOT"): return "cursor"
    #   if os.environ.get("COPILOT_..."):      return "copilot"
    return "claude-code"


__all__ = ["AgentAdapter", "get_adapter"]
