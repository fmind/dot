---
name: clipboard
description: "Copy the last requested output to the system clipboard."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/clipboard
  created: "2026-10-03"
  updated: "2026-11-10"
---

# Clipboard

`/clipboard` copies the latest requested deliverable; optional arguments select a specific output or format.

## Workflow

1. **Select the deliverable verbatim**: draft, prompt, command, snippet, table, or test output—without assistant preambles, tool logs, or surrounding code fences (unless Markdown was requested). Never regenerate or guess missing context; ask if multiple outputs fit.
1. **Pipe UTF-8 stdin to [scripts/copy.py](scripts/copy.py)** via `python -I` and structured stdin or a single-quoted heredoc (never shell interpolation or argv). Payloads >1 MiB belong in a file; pass `--keep-final-newline` when a trailing newline is part of the deliverable:

   ```bash
   python -I ~/.agents/skills/clipboard/scripts/copy.py <<'CLIPBOARD_PAYLOAD'
   The selected deliverable goes here, unchanged.
   CLIPBOARD_PAYLOAD
   ```

1. **Confirm without repeating the payload**: `copy.py` verifies the clipboard byte-for-byte. On failure, report the native diagnostic and recovery from [platform behavior](references/platforms.md) without claiming success.

## Boundaries

- **Install backends only with consent**: `xclip` or `wl-clipboard` matching the session; never `sudo`.
- **No OSC 52 in tool output**: captured stdout may never reach the user's terminal.
- **Copy ≠ paste**: replacing the clipboard never authorizes pasting or sending elsewhere.

## Documentation

- [xclip](https://github.com/astrand/xclip) · [wl-clipboard](https://github.com/bugaevc/wl-clipboard).
