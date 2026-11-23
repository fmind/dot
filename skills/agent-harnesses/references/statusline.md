---
name: statusline
description: "Configure or diagnose the managed agy status line and terminal title."
---

# Status Line and Title

Managed CLI settings invoke `~/.gemini/antigravity-cli/display.py` (`exec python3 -I -S`, Python 3.9+, stdin JSON only, control-char stripped, zero network/disk I/O) with `statusline` or `title`:

- **`statusline`**: renders ANSI + GoogleSansCode Nerd Font Mono segments separated by dim U+E0B1 (`NO_COLOR` or `TERM=dumb` emits plain text), dropping lower-priority segments on narrow widths before clipping project/activity:
  - Bold blue `project/subdir`, branch (amber `*` if dirty), and activity (`background` when idle with tasks; `needs input` on tool confirmation).
  - Full model label, custom `agent.name`, `cycle_mode` (fallback `execution_mode`), and `context N% · used/window`.
  - Running `subagents` and non-zero task/queued/artifact counts, enabled `gemini-weekly` quota (`quota N% left ↻ 5d13h`, ignoring `*-5h` and `3p-*`), colored Vim mode, and `sandbox` (amber `+net` with network).
- **`title`**: mirrors Claude Code (`✳` idle, `⚠` needs input, `◷` background, `◐` active + `conversation_title` or `project*` + `· N tasks`). Neither mode prints accounts, IDs, full paths, or transcripts.
- **Toggles & cadence**: `/statusline off` (`delete`/`reset` reverts to built-in) and `/title off` disable until next apply (`stack_with_default: true` stacks custom output below the built-in bar; `1.5.8+` overlays transient notices briefly; never set `statusLine`/`title` to a bare boolean because it drops `command`). `agy` owns refresh cadence (at most every 300ms, 5s timeout, auto-disabled after 30 consecutive failures until `/statusline enable`) and OSC 7501 ([status line](https://antigravity.google/docs/cli/statusline/), [title](https://antigravity.google/docs/cli/title/)).
