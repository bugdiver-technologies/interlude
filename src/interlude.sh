#!/bin/sh
# POSIX wrapper: locate a Python 3.8+ interpreter and exec `python -m interlude`.
#
# Falls back to `python` when `python3` isn't available. If no suitable Python
# is present at all, hook commands print `{}` and everything exits 0 -- we
# never want to break the hosting tool.

set -eu

DIR="$(cd "$(dirname "$0")" && pwd)"
CMD="${1:-}"

find_python() {
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' >/dev/null 2>&1; then
        printf '%s' "$candidate"
        return 0
      fi
    fi
  done
  return 1
}

PY="$(find_python || true)"
if [ -z "${PY}" ]; then
  case "$CMD" in
    start|stop|session-start) printf '{}\n' ;;
  esac
  exit 0
fi

# Prepend our src/ directory so `-m interlude` resolves.
if [ -n "${PYTHONPATH:-}" ]; then
  PYTHONPATH="$DIR:$PYTHONPATH"
else
  PYTHONPATH="$DIR"
fi
export PYTHONPATH

exec "$PY" -m interlude "$@"
