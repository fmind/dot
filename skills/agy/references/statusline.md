---
name: statusline
description: "Change or diagnose the managed agy status line and terminal title renderer."
---

# Status Line and Title

Managed CLI settings invoke [display.py](../scripts/display.py) (`exec python3 -I -S`, Python 3.9+, stdin JSON only, control-char stripped, zero network/disk I/O) with `statusline` or `title`. `statusline` renders ANSI + GoogleSansCode Nerd Font Mono segments separated by dim U+E0B1 (`NO_COLOR` or `TERM=dumb` emits plain text): bold blue `project/subdir`, branch (amber `*` if dirty), activity (`background` when idle with tasks; `needs input` on tool confirmation), full model label, mode, `context N% · used/window`, non-zero task/queued/artifact counts, lowest enabled family quota (`quota N% left ↻ 2h05m` with battery glyph and amber/red warnings), colored Vim mode, and `sandbox` (amber `+net` with network), dropping lower-priority segments on narrow widths before clipping project/activity.

`title` mirrors Claude Code (`✳` idle, `⚠` needs input, `◷` background, `◐` active + `conversation_title` or `project*` + `· N tasks`), stripped by [turn notifications](../../agent-harnesses/references/notifications.md); neither mode prints accounts, IDs, full paths, or transcripts. `/statusline off` and `/title off` disable them until next apply; agy owns refresh cadence and OSC 7501 ([status line](https://antigravity.google/docs/cli/statusline/), [title](https://antigravity.google/docs/cli/title/)).
