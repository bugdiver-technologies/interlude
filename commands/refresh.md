---
description: Generate a fresh batch of Interlude cards
disable-model-invocation: true
allowed-tools: Bash
---

Ask Interlude to generate a fresh batch of cards (this spends tokens via the `claude` CLI and may take up to 3 minutes). Show the user the exact output. Do not add extra commentary.

!`sh "${CLAUDE_PLUGIN_ROOT}/src/interlude.sh" refresh`
