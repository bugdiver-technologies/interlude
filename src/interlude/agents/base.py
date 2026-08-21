"""Abstract interface every host adapter implements.

An `AgentAdapter` isolates everything Interlude needs to know about the
surrounding AI coding tool:

  * How to parse the tool's hook payload (stdin JSON, env vars, ...).
  * How to answer the tool (JSON on stdout, or nothing at all).
  * How to identify the current session so per-session state can be kept.
  * How to register / unregister a status line in the tool's settings.

The rest of Interlude (cards, deck, generation, rendering) is host-agnostic
and takes an adapter as a parameter. To add support for another tool (Cursor,
Copilot, Codeium, ...), implement this interface in a new module and register
it in `interlude.agents.__init__`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AgentAdapter(ABC):
    #: Short identifier for logs / detection. e.g. "claude-code", "cursor".
    name: str = "base"

    # --- hook I/O ----------------------------------------------------------

    @abstractmethod
    def read_hook_payload(self) -> dict[str, Any]:
        """Read whatever the host passes to hook scripts (usually JSON on stdin)."""

    @abstractmethod
    def session_id_of(self, payload: dict[str, Any]) -> str:
        """Return a stable per-session identifier for state file keying."""

    @abstractmethod
    def emit_hook_ok(self) -> None:
        """Write the host's 'no-op' hook response so it doesn't inject anything into the model."""

    def transcript_path(self, payload: dict[str, Any]) -> str | None:
        """Path to the host's conversation log, when it exposes one.

        Used as a liveness signal: hosts append to it while a turn runs. Return
        None when the host has no such file, and the panel falls back to the
        turn-end hook alone.
        """
        return None

    # --- status line -------------------------------------------------------

    def supports_statusline(self) -> bool:
        """Whether this host has a status-line surface Interlude can install into."""
        return False

    def install_statusline(self, *, if_missing: bool, force: bool, silent: bool) -> str:
        """Register Interlude as the host's status line. Return a status string
        like 'installed' / 'updated' / 'skipped' / 'unsupported'."""
        return "unsupported"

    def uninstall_statusline(self) -> None:
        """Remove Interlude from the host's settings, if present."""
        return

    def is_our_statusline(self, command: Any) -> bool:
        """Whether a config value looks like our own status line entry."""
        return False
