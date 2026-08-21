"""Entry point: `python -m interlude <cmd>` and the shell wrapper both land here.

This module only parses arguments and dispatches. All real work lives in
`interlude.commands`.
"""

from __future__ import annotations

import argparse

from . import commands
from .agents import get_adapter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="interlude", description="Cards while you wait")
    parser.add_argument(
        "--agent",
        default=None,
        help="Override host detection (e.g. `claude-code`). Rarely needed.",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("start", help="Turn-start hook: record marker for this session")
    sub.add_parser("stop", help="Turn-end hook: clear marker for this session")
    sub.add_parser("session-start", help="Session-start hook: install status line if the host supports it")
    sub.add_parser("statusline", help="Render the current card for the host's status line")
    sub.add_parser("demo", help="Preview a few cards")
    sub.add_parser("refresh", help="Manually top up the user deck via the LLM CLI")
    sub.add_parser("generate", help="(internal) Synchronous generation. Spawned in the background by hooks.")
    sub.add_parser("status", help="Show deck stats")
    install = sub.add_parser("install", help="Register Interlude as the host's status line")
    install.add_argument("--force", action="store_true")
    install.add_argument("--if-missing", action="store_true")
    sub.add_parser("uninstall", help="Remove Interlude from the host's status line")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    adapter = get_adapter(args.agent)

    if args.cmd == "start":
        commands.start(adapter)
    elif args.cmd == "stop":
        commands.stop(adapter)
    elif args.cmd == "session-start":
        commands.session_start(adapter)
    elif args.cmd == "statusline":
        commands.statusline(adapter)
    elif args.cmd == "demo":
        commands.demo()
    elif args.cmd == "refresh":
        commands.refresh()
    elif args.cmd == "generate":
        commands.generate_now()
    elif args.cmd == "status":
        commands.status()
    elif args.cmd == "install":
        commands.install(adapter, if_missing=args.if_missing, force=args.force)
    elif args.cmd == "uninstall":
        commands.uninstall(adapter)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
