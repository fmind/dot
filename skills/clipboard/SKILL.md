---
name: clipboard
description: "Copy the last requested output to the system clipboard."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/clipboard
  created: "2026-10-03"
  updated: "2026-10-05"
---

# Clipboard

Treat `/clipboard` without arguments as “copy the interesting output I requested in the preceding exchange.” Arguments can select a particular result or format.

## Workflow

1. **Select the latest requested deliverable**: a draft, prompt, command, code snippet, table, or test result. Omit assistant preambles, progress updates, tool logs, and offers to continue unless they are the requested output. Preserve the deliverable verbatim; do not regenerate it or rerun a test. For code or commands, omit the surrounding Markdown fence unless the user requested Markdown. If several outputs are equally plausible, ask which one; never guess unavailable conversation content.
1. **Pipe the text to the helper**: pass the selected UTF-8 text to [scripts/copy.py](scripts/copy.py) on stdin using `python -I`. Use the tool's structured stdin when available, or a single-quoted heredoc with a delimiter absent from the text; never interpolate the content into shell commands or command-line arguments. The helper strips exactly one final newline, the one a heredoc always adds; pass `--keep-final-newline` when the deliverable must end with one, such as a whole file.

   ```bash
   python -I ~/.agents/skills/clipboard/scripts/copy.py <<'CLIPBOARD_PAYLOAD'
   The selected deliverable goes here, unchanged.
   CLIPBOARD_PAYLOAD
   ```

1. **Confirm briefly what was copied**: do not repeat the payload. The helper checks the clipboard byte for byte and reports success only after verification. If it fails, report the cause, including the native tool's diagnostic it prints, and the relevant recovery from [platform behavior](references/platforms.md); do not claim that the clipboard was updated successfully.

## Boundaries

- **Install the matching Linux backend**: for a missing backend, install the one matching the display server (`xclip` or `wl-clipboard`; macOS has `pbcopy` built in); do not use sudo or install tools silently.
- **Avoid OSC 52 in tool output**: do not emit OSC 52 escape sequences through tool output; captured output may never reach the user's terminal.
- **Copying does not authorize pasting**: invocation authorizes replacing the current clipboard; it does not authorize pasting into an application or sending the content elsewhere.

## Documentation

- [xclip](https://github.com/astrand/xclip) · [wl-clipboard](https://github.com/bugaevc/wl-clipboard).
