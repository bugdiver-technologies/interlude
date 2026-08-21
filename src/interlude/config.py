"""All tunable constants and canonical paths for Interlude."""

from __future__ import annotations

import os
from pathlib import Path

# Package + repo roots -------------------------------------------------------

PACKAGE_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PACKAGE_ROOT.parent
REPO_ROOT = SRC_ROOT.parent

BUNDLED_CARDS = REPO_ROOT / "data" / "cards.json"
WRAPPER_SCRIPT = SRC_ROOT / "interlude.sh"

# User cache -----------------------------------------------------------------

USER_DIR = Path.home() / ".interlude"
USER_DECK = USER_DIR / "deck.json"
SEEN_FILE = USER_DIR / "seen.txt"
LAST_GEN_FILE = USER_DIR / "last_generated"


def state_dir() -> Path:
    """Per-user ephemeral state directory used for turn markers."""
    return Path(f"/tmp/interlude-{os.getuid()}")


# Timing (seconds) -----------------------------------------------------------

SHOW_DELAY_SEC = 1
ROTATE_SEC = 12
REVEAL_AFTER_SEC = 8
STALE_SEC = 900
CARDS_PER_TURN = 6

# How long the host's transcript may sit untouched before we treat the turn as
# over. Generous enough to survive a long API call with no streamed output.
TRANSCRIPT_IDLE_SEC = 45

# Generation -----------------------------------------------------------------

GEN_LOW_THRESHOLD = 20   # top up when unseen pool drops below this
GEN_THROTTLE_SEC = 3600  # at most one automatic refresh per hour
GEN_TARGET = 40          # cards requested per generation
GEN_TIMEOUT_SEC = 180    # max wall time for the LLM subprocess

# Identifiers ----------------------------------------------------------------

STATUSLINE_MARKER = "interlude-statusline"

# Rendering ------------------------------------------------------------------

LETTERS = "ABCD"
DIM = "\033[2m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RESET = "\033[0m"
