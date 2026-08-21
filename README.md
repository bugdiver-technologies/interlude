# Interlude

A Claude Code plugin that shows a small rotating card — trivia, facts, tips, or jokes — in the status line **while Claude is working**. Wait time feels less dead.

Cards are display only. They never enter Claude's context, never travel through `additionalContext`, and never appear in the transcript.

## Install

### From the marketplace

In Claude Code:

```text
/plugin marketplace add BugDiver-Technologies/interlude
/plugin install interlude@interlude
```

Reload plugins if Claude asks (`/reload-plugins`). On the next session, Interlude installs its status line if you do not already have a custom one.

While the plugin is enabled, two slash commands are available when Claude is idle:

| Command | What it does |
|---|---|
| `/interlude:status` | Deck stats |
| `/interlude:refresh` | Generate a fresh batch of cards |

These go through the chat, so they queue if you type them while Claude is already working. Use them between turns.

### From source

```bash
git clone https://github.com/BugDiver-Technologies/interlude.git
cd interlude
chmod +x src/interlude.sh
sh src/interlude.sh demo         # optional: preview a few cards
sh src/interlude.sh install      # register the status line in ~/.claude/settings.json
claude --plugin-dir .
```

`--plugin-dir .` loads this checkout for one session. For a lasting local install, add the clone as a marketplace (`/plugin marketplace add /path/to/interlude`) and install `interlude@interlude`.

## Try it

Send a prompt that takes more than a second. The card fades in ~1s after submit, cards rotate every ~12s, trivia auto-reveals its answer after ~8s, and the panel disappears when Claude finishes. Answers are auto-revealed on a timer — there's no input path (typing `A`/`B`/`C`/`D` in chat would become a real prompt).

## Cards

Two decks, merged at render time:

- **Bundled** — `data/cards.json`, always available.
- **Generated** — `~/.interlude/deck.json`, produced in the background by shelling out to `claude -p …` on first install and again whenever the unseen pool is running low (throttled to at most once per hour). Silently no-ops if the `claude` CLI isn't on `PATH`.

Manual controls:

```bash
sh src/interlude.sh refresh     # force a generation now (ignores throttle)
sh src/interlude.sh status      # deck stats (total / unseen / last gen)
sh src/interlude.sh hide        # mute the status line
sh src/interlude.sh show        # unmute after hide
sh src/interlude.sh uninstall   # remove Interlude's status line
```

Generation spends tokens under your account. Remove `claude` from `PATH` while running Claude Code to disable auto-generation.

## Requirements

- Claude Code 2.1.153+ (checked against 2.1.227)
- `python3` **or** `python` (≥ 3.8) reachable via `PATH`
- POSIX `sh` (macOS, Linux, WSL, Git Bash)
- Optional: `claude` CLI on `PATH` for background card generation

## How it works

Claude Code's plugin surfaces either inject into the model (`additionalContext`, monitors, channels, sub-agents) or belong to the user's chat (slash commands, prompt box). Two surfaces are both silent and human-visible, and Interlude uses only these:

- **Hooks** observe the turn lifecycle and write a tiny per-session marker under `/tmp/interlude-$UID/`. They emit only `{}` on stdout so nothing reaches the model.
- **Status line** reads the marker, picks a card by elapsed time, and prints ANSI. Its stdout is TUI-only and does not consume tokens.

The turn-end hook normally clears the marker, but it cannot fire if you disable the plugin or kill Claude mid-turn. So the status line also hides the panel once the session transcript has sat untouched for `TRANSCRIPT_IDLE_SEC`, and ignores markers older than `STALE_SEC` outright.

Note that the status line is Claude's own setting rather than a plugin surface, so disabling the plugin leaves it registered. Run `sh src/interlude.sh uninstall` to remove it.

The `src/interlude.sh` wrapper finds a suitable Python interpreter and hands off to `python -m interlude`; if none is available, the wrapper emits `{}` and exits so hooks never break Claude Code.
