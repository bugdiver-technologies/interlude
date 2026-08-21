"""High-level commands, host-agnostic. Each function receives an adapter
where host behaviour is needed and delegates for I/O and settings.

Hook commands (`start`, `stop`, `session_start`) always emit the host's OK
response, even on internal errors — we never want to break the hosting tool.
"""

from __future__ import annotations

import random
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from . import cards as card_deck
from . import generate
from .agents.base import AgentAdapter
from .config import (
    CARDS_PER_TURN,
    LAST_GEN_FILE,
    ROTATE_SEC,
    REVEAL_AFTER_SEC,
    SHOW_DELAY_SEC,
    STALE_SEC,
    USER_DECK,
    state_dir,
)
from .io_utils import atomic_write_json, read_json
from .render import render_panel


# --- marker helpers ---------------------------------------------------------

def _state_path(session_id: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in session_id)
    return state_dir() / f"{safe}.json"


def _write_marker(session_id: str, marker: dict[str, Any]) -> None:
    atomic_write_json(_state_path(session_id), marker)


def _read_marker(session_id: str) -> dict[str, Any] | None:
    data = read_json(_state_path(session_id))
    return data if isinstance(data, dict) else None


def _clear_marker(session_id: str) -> None:
    try:
        _state_path(session_id).unlink()
    except FileNotFoundError:
        pass


# --- hook commands ----------------------------------------------------------

def start(adapter: AgentAdapter) -> None:
    try:
        payload = adapter.read_hook_payload()
        session_id = adapter.session_id_of(payload)
        turn_cards = card_deck.pick_turn_cards(CARDS_PER_TURN)
        _write_marker(session_id, {"started_at": int(time.time()), "cards": turn_cards})
        generate.spawn_background_generate()
    except Exception:
        pass
    adapter.emit_hook_ok()


def stop(adapter: AgentAdapter) -> None:
    try:
        payload = adapter.read_hook_payload()
        session_id = adapter.session_id_of(payload)
        _clear_marker(session_id)
    except Exception:
        pass
    adapter.emit_hook_ok()


def session_start(adapter: AgentAdapter) -> None:
    try:
        adapter.read_hook_payload()
        if adapter.supports_statusline():
            adapter.install_statusline(if_missing=True, force=False, silent=True)
        generate.spawn_background_generate()
    except Exception:
        pass
    adapter.emit_hook_ok()


# --- status line ------------------------------------------------------------

def statusline(adapter: AgentAdapter) -> None:
    """Read the current-turn marker and print the current card, if any."""
    try:
        payload = adapter.read_hook_payload()
        session_id = adapter.session_id_of(payload)
    except Exception:
        return
    marker = _read_marker(session_id)
    if marker is None:
        return
    started = marker.get("started_at")
    if not isinstance(started, (int, float)):
        return
    if time.time() - started > STALE_SEC:
        return
    elapsed = int(time.time()) - int(started)
    if elapsed < SHOW_DELAY_SEC:
        return
    turn_cards = marker.get("cards")
    if not isinstance(turn_cards, list) or not turn_cards:
        return
    slot = (elapsed // ROTATE_SEC) % len(turn_cards)
    elapsed_in_card = elapsed - (elapsed // ROTATE_SEC) * ROTATE_SEC
    sys.stdout.write(render_panel(turn_cards[slot], elapsed_in_card) + "\n")


# --- host-agnostic user commands --------------------------------------------

def demo() -> None:
    deck = card_deck.load_deck()
    if not deck:
        print("No cards found.", file=sys.stderr)
        return
    sample = random.sample(deck, min(4, len(deck)))
    for i, card in enumerate(sample):
        print(render_panel(card, REVEAL_AFTER_SEC if i % 2 else 0))
        print()


def refresh() -> None:
    if not shutil.which("claude"):
        print("`claude` CLI not found on PATH. Skipping refresh.", file=sys.stderr)
        return
    generate.mark_gen_started()
    print("Asking Claude for a fresh batch of cards. This may take up to 3 minutes...", file=sys.stderr)
    added = generate.run_generation()
    total = len(card_deck.load_user_deck())
    print(f"Added {added} cards. User deck now has {total} cards.", file=sys.stderr)


def status() -> None:
    deck = card_deck.load_deck()
    user = card_deck.load_user_deck()
    bundled_count = max(len(deck) - len(user), 0)
    seen = card_deck.load_seen()
    print(f"Total deck:  {len(deck)} cards ({len(user)} generated, {bundled_count} bundled)")
    print(f"Unseen:      {sum(1 for c in deck if c['id'] not in seen)} cards")
    print(f"Seen ids:    {len(seen)}")
    age = generate.gen_last_run_age_sec()
    print(f"Last gen:    {'never' if age is None else f'{age}s ago'}")


def generate_now() -> None:
    """Background entry point — spawn_background_generate() invokes this."""
    generate.run_generation()


def install(adapter: AgentAdapter, *, if_missing: bool = False, force: bool = False) -> None:
    if not adapter.supports_statusline():
        print(f"Host `{adapter.name}` has no status line to install.", file=sys.stderr)
        return
    adapter.install_statusline(if_missing=if_missing, force=force, silent=False)


def uninstall(adapter: AgentAdapter) -> None:
    if not adapter.supports_statusline():
        print(f"Host `{adapter.name}` has no status line to uninstall.", file=sys.stderr)
        return
    adapter.uninstall_statusline()
