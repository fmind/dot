---
name: continuation
description: "Resume, compact, or fork agy and Claude Code sessions, or copy a handoff prompt before /clear."
---

# Continuation

Prefer native host resume or compaction; write a handoff only when conversation history will not carry over. [agy](../../agy/SKILL.md) owns other agy session features.

## Choose the path

- **Same agy session**: `agy -c` (latest), `agy --conversation <id>`, or `/resume` in-session.
- **Long agy session**: `/compact [message]` summarizes context and answers `message`; `/context` shows usage.
- **Branching**: `/fork` clones conversation history only; pair with [git-worktree](../../git-delivery/references/git-worktree/GUIDE.md) for parallel edits.
- **Claude Code** (verified 2.1.319): `claude -c` (latest in cwd), `claude --resume <id-or-name>` (`-r`, or picker), `/compact [instructions]`, `/rewind` (conversation/code checkpoint), and `--fork-session` (new session ID).
- **Fresh start**: save and copy a handoff below, run `/clear`, and paste the prompt or pointer line.

## Handoff workflow

1. **Freeze state**: record `git status --short --branch`, `git rev-parse --short HEAD`, staged vs unstaged paths, worktrees, and live `/tasks`, servers, or subagents with handles/PIDs (stop nothing).
1. **Write** using the [parent sections](../SKILL.md), prioritizing: objective and authority, user corrections and rejected approaches (quoted when exact wording matters), current state with proof and imperative next step, failed approaches, and needed `path:line`/log/task handles. Omit tool narration, passing logs, repo/`AGENTS.md` rules, secrets, and private text. Append verbatim:

   ```markdown
   ## Resume

   Read this whole file. Compare `git status --short --branch` and `git rev-parse --short HEAD` with the recorded state and report any drift before acting. Reuse recorded proof only while its inputs are unchanged, start at the next step, and keep the recorded authority boundaries. Delete this file once the work lands; it is task-owned scratch.
   ```

1. **Save** as `<YYYY-MM-DD>-handoff-<slug>.md` in the [parent inbox](../SKILL.md), adding a suffix instead of overwriting.
1. **Copy** via [clipboard](../../clipboard/SKILL.md) without shell-quoting content; if requested or over ~8,000 chars, copy `Continue from <absolute path>: read it fully, verify the recorded state, then do the next step.` instead:

   ```bash
   python -I ~/.agents/skills/clipboard/scripts/copy.py < "$handoff"
   ```

1. **Confirm** saved path, copied form (full vs pointer), and any background work that may need restarting after `/clear`.

## Gotchas

- **Authority never expands**: record only existing approvals, exact staged selections, and whether conversation-bound background tasks stop on `/clear`.

## Documentation

- [Antigravity conversations](https://antigravity.google/docs/cli/conversations/) · `agy --help`
- [Claude Code sessions](https://code.claude.com/docs/en/sessions) · [checkpointing](https://code.claude.com/docs/en/checkpointing) · `claude --help`
