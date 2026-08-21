"""Background card generation via a local LLM CLI.

Currently supports the `claude` CLI (`claude -p '<prompt>'`). If that binary
isn't on PATH the generator no-ops. Multiple providers can be added by
generalising the `_run_llm` function.

Design goals:
  * Never block a hook. Generation runs detached (`start_new_session`).
  * Never spend more tokens than needed. A throttle and a low-water threshold
    together decide whether to launch.
  * Never crash the plugin. All filesystem writes swallow OSError.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .cards import Card, load_deck, normalise, unseen_count, validate
from .config import (
    GEN_LOW_THRESHOLD,
    GEN_TARGET,
    GEN_THROTTLE_SEC,
    GEN_TIMEOUT_SEC,
    LAST_GEN_FILE,
    USER_DECK,
    USER_DIR,
)
from .io_utils import read_json


# --- throttle ---------------------------------------------------------------

def _within_throttle() -> bool:
    try:
        last = float(LAST_GEN_FILE.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError, OSError):
        return False
    return time.time() - last <= GEN_THROTTLE_SEC


def should_generate() -> bool:
    """Decide whether background generation should be spawned right now.

    Policy:
      1. If a generation ran within the throttle window, skip regardless.
      2. If the user deck does not exist yet (first install), always generate —
         the bundled deck is only a fallback until Claude has produced fresh
         cards.
      3. Otherwise, only generate when the unseen pool has dropped below the
         low-water threshold.
    """
    if _within_throttle():
        return False
    if not USER_DECK.exists():
        return True
    return unseen_count() < GEN_LOW_THRESHOLD


def mark_gen_started() -> None:
    try:
        USER_DIR.mkdir(parents=True, exist_ok=True)
        LAST_GEN_FILE.write_text(str(time.time()), encoding="utf-8")
    except OSError:
        return


def gen_last_run_age_sec() -> int | None:
    try:
        last = float(LAST_GEN_FILE.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError, OSError):
        return None
    return int(time.time() - last)


# --- prompt + parsing -------------------------------------------------------

def build_prompt(count: int, avoid_titles: list[str]) -> str:
    avoid_json = json.dumps(avoid_titles[:60], ensure_ascii=False)
    return (
        f"Generate exactly {count} short cards for a 'while you wait' UI. "
        "Output ONLY a JSON array. No prose. No markdown. No backticks. "
        "Each item is exactly one of:\n"
        '{"type":"trivia","q":"...","options":["a","b","c","d"],"answer":<0-3>,"why":"..."}\n'
        '{"type":"fact","text":"..."}\n'
        '{"type":"tip","text":"..."}\n'
        '{"type":"joke","text":"..."}\n'
        "Rules: mix types with roughly equal variety; each field under 180 chars; "
        "trivia options are short (each < 40 chars); jokes are clean and one-liner style; "
        "tips are practical CLI/dev tips. "
        f"Do NOT repeat these existing titles: {avoid_json}"
    )


def parse_cards(text: str) -> list[Card]:
    if not text:
        return []
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    start = stripped.find("[")
    end = stripped.rfind("]")
    if start < 0 or end <= start:
        return []
    try:
        arr = json.loads(stripped[start : end + 1])
    except json.JSONDecodeError:
        return []
    if not isinstance(arr, list):
        return []
    return [c for c in arr if validate(c)]


# --- provider shim ----------------------------------------------------------

def _claude_available() -> bool:
    return shutil.which("claude") is not None


def _run_llm(prompt: str, timeout: int) -> str | None:
    """Run whichever CLI provider is available. Currently just `claude`."""
    if not _claude_available():
        return None
    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


# --- merge ------------------------------------------------------------------

def merge_into_user_deck(new_cards: list[Card]) -> int:
    if not new_cards:
        return 0
    try:
        USER_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        return 0
    existing_raw = read_json(USER_DECK) or []
    if not isinstance(existing_raw, list):
        existing_raw = []
    seen_ids: set[str] = set()
    combined: list[Card] = []
    added = 0
    for source, is_new in ((existing_raw, False), (new_cards, True)):
        for card in source:
            if not validate(card):
                continue
            normalised = normalise(card)
            if normalised["id"] in seen_ids:
                continue
            seen_ids.add(normalised["id"])
            combined.append(normalised)
            if is_new:
                added += 1
    try:
        tmp = USER_DECK.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(USER_DECK)
    except OSError:
        return 0
    return added


# --- entry points -----------------------------------------------------------

def run_generation() -> int:
    """Synchronously ask the LLM for a batch and merge. Returns cards added."""
    existing = load_deck()
    avoid = [str(c.get("q") or c.get("text") or "") for c in existing[-80:]]
    prompt = build_prompt(GEN_TARGET, avoid)
    stdout = _run_llm(prompt, GEN_TIMEOUT_SEC)
    if stdout is None:
        return 0
    return merge_into_user_deck(parse_cards(stdout))


def spawn_background_generate() -> None:
    """Fire-and-forget: launch `python -m interlude generate` detached."""
    if not should_generate() or not _claude_available():
        return
    mark_gen_started()
    try:
        subprocess.Popen(
            [sys.executable, "-m", "interlude", "generate"],
            start_new_session=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
    except OSError:
        return
