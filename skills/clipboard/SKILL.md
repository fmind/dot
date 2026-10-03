---
name: clipboard
description: "Copy the requested deliverable from the preceding exchange to the system clipboard on macOS or ChromeOS/Linux."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/clipboard
  created: "2026-10-03"
  updated: "2026-10-03"
---

# Clipboard

Treat `/clipboard` without arguments as “copy the interesting output I requested in the preceding exchange.” Arguments can select a particular result or format.

## Workflow

1. Select the latest requested deliverable: a draft, prompt, command, code snippet, table, or test result. Omit assistant preambles, progress updates, tool logs, and offers to continue unless they are the requested output. Preserve the deliverable verbatim; do not regenerate it or rerun a test. For code or commands, omit the surrounding Markdown fence unless the user requested Markdown. If several outputs are equally plausible, ask which one; never guess unavailable conversation content.
1. Pass the selected UTF-8 text to [scripts/copy.py](scripts/copy.py) on stdin using `python`. Use the tool's structured stdin when available, or a single-quoted heredoc with a delimiter absent from the text; never interpolate the content into shell commands or command-line arguments. A heredoc adds a final newline: account for it when exact trailing bytes matter.

   ```bash
   python ~/.agents/skills/clipboard/scripts/copy.py <<'CLIPBOARD_PAYLOAD'
   The selected deliverable goes here, unchanged.
   CLIPBOARD_PAYLOAD
   ```

1. Confirm briefly what was copied, without repeating the payload. The helper checks the clipboard byte for byte and reports success only after verification. If it fails, report the cause and the relevant recovery; do not claim that the clipboard was updated successfully.

## Platform behavior

- **macOS**: built-in `pbcopy` and `pbpaste`.
- **ChromeOS/Linux**: prefer `xclip -selection clipboard` with `DISPLAY`, following this workstation's Crostini convention; otherwise use `wl-copy` and `wl-paste` with `WAYLAND_DISPLAY`. These tools are already installed on the current ChromeOS host. A different Linux host needs one matching its display server; do not use sudo or install tools silently.
- Each native command has a five-second timeout. Failures leave the clipboard state uncertain; a backend error does not trigger another write. Headless/remote shells without a local clipboard fail explicitly. Do not emit OSC 52 escape sequences through tool output: captured output may never reach the user's terminal.
- The helper accepts plain UTF-8 text, preserves newlines, rejects empty input, and does not print or retain clipboard contents. Invocation authorizes replacing the current clipboard; it does not authorize pasting into an application or sending the content elsewhere.

## Documentation

- [xclip](https://github.com/astrand/xclip) · [wl-clipboard](https://github.com/bugaevc/wl-clipboard).
