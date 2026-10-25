---
name: continuation
description: "Resume, compact, or fork an agy session, or save and copy a handoff prompt before /clear."
---

# Continuation

Let the next session continue without the user re-explaining. Prefer agy's native session tools, which keep the full history; write a handoff prompt only when the conversation itself will not carry over. The [agy skill](../../agy/SKILL.md) owns other session features.

## Choose the path

- **Same conversation later**: `agy -c` resumes the most recent conversation, `agy --conversation <id>` a specific one, and `/resume` picks one inside the session. No handoff is needed.
- **Long session**: `/compact [message]` summarizes the conversation to free context, then answers `message` if given; `/context` shows usage.
- **Alternative approach**: `/fork` copies the conversation history, not the checkout or a Git branch; use [git-worktree](../../git-delivery/references/git-worktree/GUIDE.md) for competing edits.
- **Fresh start**: write and copy a handoff with the workflow below, then `/clear`, which clears the conversation and starts a new one. Paste the handoff, or its pointer line, as the first prompt.

## Handoff workflow

1. **Freeze the state**: `git status --short --branch`, `git rev-parse --short HEAD`, staged versus unstaged work, worktrees, and anything still running: background commands (`/tasks`), servers, and subagents. Stop nothing; record what is running, its handle or PID, and how to check on it.
1. **Write the continuation** from the [prompt template](prompt-template.md). When space is short, keep in this order: objective and authority, the user's latest corrections and rejected approaches (quoted when the wording matters), current state with proof and the next step as an imperative, failed approaches, then the paths, logs, and running-work handles the next session needs, citing paths and lines instead of pasting code. Omit tool narration, passing logs, and anything the repository or AGENTS.md already states. Write it for a reader without this conversation; never include secrets or private passages. End with this fixed block, because the receiving session will not have this guide loaded:

   ```markdown
   ## Resume

   Read this whole file. Compare `git status --short --branch` and `git rev-parse --short HEAD` with the recorded state and report any drift before acting. Reuse recorded proof only while its inputs are unchanged, start at the next step, and keep the recorded authority boundaries. Delete this file once the work lands; it is task-owned scratch.
   ```

1. **Save** where the parent [skill](../SKILL.md) saves prompts, as `<YYYY-MM-DD>-handoff-<slug>.md`. Never overwrite an existing handoff; add a suffix.
1. **Copy** the file itself with [clipboard](../../clipboard/SKILL.md), which avoids quoting the content into a shell command. When the user asks for a pointer, or the prompt exceeds about 8,000 characters, copy one line instead: `Continue from <absolute path>: read it fully, verify the recorded state, then do the next step.`

   ```bash
   python -I ~/.agents/skills/clipboard/scripts/copy.py < "$handoff"
   ```

1. **Confirm**: the saved path, what was copied (full prompt or pointer), and anything still running that the user should know about before clearing.

## Gotchas

- **Authority does not grow**: a handoff records approvals already given; it never turns a proposal into an authorized action.
- **Record staged selections exactly**: the next session must not restage or commit unrelated work.
- **Flag running work for restart**: a background command started by this conversation may stop with it; say whether it must be restarted.

## Documentation

- [Antigravity conversations](https://antigravity.google/docs/cli/conversations/) · `agy --help` for resume flags
