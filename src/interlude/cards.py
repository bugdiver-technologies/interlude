"""Card model, deck loading, and per-turn selection with seen-tracking.

A card is a small dict of one of these shapes:

    {"type": "trivia", "q": str, "options": [str, str, str, str], "answer": 0-3, "why": str}
    {"type": "fact",   "text": str}
    {"type": "tip",    "text": str}
    {"type": "joke",   "text": str}

Cards are normalised on load: an "id" field is added (10-char sha1 of type + primary text).
Host-agnostic — no adapter needed to load or pick cards.
"""

from __future__ import annotations

import hashlib
import random
from pathlib import Path
from typing import Any

from .config import BUNDLED_CARDS, SEEN_FILE, USER_DECK, USER_DIR
from .io_utils import read_json

Card = dict[str, Any]


# --- model ------------------------------------------------------------------

def card_id(card: Card) -> str:
    text = str(card.get("q") or card.get("text") or "")
    key = f"{card.get('type', '')}::{text}".strip().lower()
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]


def normalise(card: Card) -> Card:
    result = dict(card)
    result["id"] = card_id(card)
    return result


def validate(card: Any) -> bool:
    if not isinstance(card, dict):
        return False
    kind = card.get("type")
    if kind == "trivia":
        q = card.get("q")
        options = card.get("options")
        if not isinstance(q, str) or not q.strip():
            return False
        if not isinstance(options, list) or len(options) != 4:
            return False
        if not all(isinstance(o, str) and o.strip() for o in options):
            return False
        try:
            answer = int(card.get("answer"))
        except (TypeError, ValueError):
            return False
        return 0 <= answer < 4
    if kind in {"fact", "tip", "joke"}:
        text = card.get("text")
        return isinstance(text, str) and bool(text.strip())
    return False


# --- deck loading -----------------------------------------------------------

def _load_from(path: Path) -> list[Card]:
    data = read_json(path)
    if not isinstance(data, list):
        return []
    return [normalise(c) for c in data if validate(c)]


def load_user_deck() -> list[Card]:
    return _load_from(USER_DECK)


def load_bundled_deck() -> list[Card]:
    return _load_from(BUNDLED_CARDS)


def load_deck() -> list[Card]:
    """User deck first, then bundled, deduplicated by id."""
    seen_ids: set[str] = set()
    combined: list[Card] = []
    for source in (load_user_deck(), load_bundled_deck()):
        for card in source:
            if card["id"] in seen_ids:
                continue
            seen_ids.add(card["id"])
            combined.append(card)
    return combined


# --- seen tracking ----------------------------------------------------------

def load_seen() -> set[str]:
    try:
        return {line.strip() for line in SEEN_FILE.read_text(encoding="utf-8").splitlines() if line.strip()}
    except (FileNotFoundError, OSError):
        return set()


def append_seen(ids: list[str]) -> None:
    if not ids:
        return
    try:
        USER_DIR.mkdir(parents=True, exist_ok=True)
        with SEEN_FILE.open("a", encoding="utf-8") as handle:
            for value in ids:
                handle.write(value + "\n")
    except OSError:
        # Seen tracking is a nice-to-have. If home is unwritable cards will
        # just cycle sooner.
        return


def reset_seen() -> None:
    try:
        SEEN_FILE.unlink()
    except (FileNotFoundError, OSError):
        pass


def unseen_count() -> int:
    deck = load_deck()
    if not deck:
        return 0
    seen = load_seen()
    return sum(1 for c in deck if c["id"] not in seen)


# --- turn selection ---------------------------------------------------------

def pick_turn_cards(n: int) -> list[Card]:
    """Pick n unseen cards for a single turn. Rotates through the deck; when
    every card has been seen, resets and starts over."""
    deck = load_deck()
    if not deck:
        return []
    seen = load_seen()
    unseen = [c for c in deck if c["id"] not in seen]
    if len(unseen) < n:
        reset_seen()
        unseen = deck[:]
    random.shuffle(unseen)
    picked = unseen[: min(n, len(unseen))]
    append_seen([c["id"] for c in picked])
    return picked
