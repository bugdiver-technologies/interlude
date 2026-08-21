"""Host-agnostic ANSI panel rendering.

Cards go in; a bordered, colour-annotated block goes out. The renderer only
knows about the abstract card shape and terminal width; it never touches
files, subprocesses, or hook I/O.
"""

from __future__ import annotations

import os
from typing import Any

from .cards import Card
from .config import CYAN, DIM, GREEN, LETTERS, REVEAL_AFTER_SEC, RESET, YELLOW


def visible_width(text: str) -> int:
    """Character width for terminal layout. Treats large-BMP glyphs (emoji)
    as double-wide."""
    width = 0
    for char in text:
        width += 2 if ord(char) > 0x1F000 else 1
    return width


def pad(text: str, inner: int) -> str:
    if visible_width(text) > inner:
        while text and visible_width(text) > inner - 1:
            text = text[:-1]
        text = text + "…"
    return text + " " * max(inner - visible_width(text), 0)


def wrap(text: str, inner: int) -> list[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        candidate = word if not current else current + " " + word
        if visible_width(candidate) <= inner:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word if visible_width(word) <= inner else word[: max(inner - 1, 1)] + "…"
    if current:
        lines.append(current)
    return lines or [""]


def option_row(options: list[str], inner: int) -> list[str]:
    labeled = [f"{LETTERS[i]}) {opt}" for i, opt in enumerate(options[:4])]
    joined = "   ".join(labeled)
    if visible_width(joined) <= inner:
        return [joined]
    if len(labeled) == 4:
        row1 = "   ".join(labeled[:2])
        row2 = "   ".join(labeled[2:])
        if visible_width(row1) <= inner and visible_width(row2) <= inner:
            return [row1, row2]
    return labeled


# --- per-type body ---------------------------------------------------------

def _render_trivia(card: Card, elapsed_in_card: int, inner: int) -> list[tuple[str, str]]:
    q = str(card.get("q") or "")
    options = [str(o) for o in (card.get("options") or [])]
    try:
        answer = int(card.get("answer", 0))
    except (TypeError, ValueError):
        answer = 0
    revealed = elapsed_in_card >= REVEAL_AFTER_SEC
    body: list[tuple[str, str]] = []
    for line in wrap(q, inner):
        body.append(("", line))
    body.append(("", ""))
    for line in option_row(options, inner):
        body.append(("", line))
    if revealed and 0 <= answer < len(options):
        body.append(("", ""))
        body.append((GREEN, f"Answer: {LETTERS[answer]}) {options[answer]}"))
        why = str(card.get("why") or "").strip()
        if why:
            for line in wrap(why, inner):
                body.append((DIM, line))
    return body


def _render_text(header: str, header_color: str, card: Card, inner: int) -> list[tuple[str, str]]:
    text = str(card.get("text") or "").strip()
    body: list[tuple[str, str]] = [(header_color, header), ("", "")]
    for line in wrap(text, inner):
        body.append(("", line))
    return body


def _render_card_body(card: Card, elapsed_in_card: int, inner: int) -> list[tuple[str, str]]:
    kind = str(card.get("type") or "").lower()
    if kind == "trivia":
        return _render_trivia(card, elapsed_in_card, inner)
    if kind == "tip":
        return _render_text("Tip", CYAN, card, inner)
    if kind == "joke":
        return _render_text("Joke", YELLOW, card, inner)
    return _render_text("Did you know?", CYAN, card, inner)


# --- panel -----------------------------------------------------------------

def render_panel(card: Card, elapsed_in_card: int) -> str:
    columns = int(os.environ.get("COLUMNS") or 72)
    inner = max(36, min(64, columns - 4))
    title = "🧠 Interlude"
    body = _render_card_body(card, elapsed_in_card, inner)
    top = f"╭─ {title} " + "─" * max(inner - visible_width(title) - 1, 1) + "╮"
    bottom = "╰" + "─" * (inner + 2) + "╯"
    lines = [top]
    for color, text in body:
        padded = pad(text, inner)
        if color:
            lines.append(f"│ {color}{padded}{RESET} │")
        else:
            lines.append(f"│ {padded} │")
    lines.append(bottom)
    return "\n".join(lines)
