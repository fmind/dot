---
name: handoff
description: "Save and copy a continuation prompt before /clear or switching harnesses."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/handoff
  created: "2026-10-04"
  updated: "2026-10-05"
---

# Handoff

Treat `/handoff` as "I am about to clear this session or move to another harness; let the next one continue without me re-explaining." It writes a continuation in the [task-prompts](../task-prompts/SKILL.md) format, saves it, and copies it with [clipboard](../clipboard/SKILL.md). Arguments can name a focus, a receiving harness, or `pointer` to copy only the file reference. Native resume (`claude --resume`, `codex resume`, or `codex fork` to branch) is better when the same harness continues with the full history.

## Workflow

1. **Freeze the state**: `git status --short --branch`, `git rev-parse --short HEAD`, staged versus unstaged work, worktrees, and anything still running: background shells, servers, monitors, subagents, scheduled wakeups. Stop nothing; record what is running, its handle or PID, and how to check on it.
1. **Write the continuation** from the [prompt template](../task-prompts/references/prompt-template.md). When space is short, keep in this order: objective and authority, the user's latest corrections and rejected approaches (quoted when the wording matters), current state with proof and the next step as an imperative, failed approaches, then the paths, logs, and running-work handles the next session needs, citing paths and lines instead of pasting code. Omit tool narration, passing logs, and anything the repository or AGENTS.md already states. Write it for a reader without this conversation; never include secrets or private passages. End with this fixed block, because the receiving session will not have this skill loaded:

   ```markdown
   ## Resume

   Read this whole file. Compare `git status --short --branch` and `git rev-parse --short HEAD` with the recorded state and report any drift before acting. Reuse recorded proof only while its inputs are unchanged, start at the next step, and keep the recorded authority boundaries. Delete this file once the work lands; it is task-owned scratch.
   ```

1. **Save**: in a repository, `.agents/prompts/<YYYY-MM-DD>-handoff-<slug>.md` under `git rev-parse --show-toplevel` (gitignored globally); outside one, `~/.agents/prompts/`. Never overwrite an existing handoff; add a suffix.
1. **Copy**: send the file itself, which avoids quoting the content into a shell command. With `pointer`, or when the prompt exceeds about 8,000 characters, copy one line instead: `Continue from <absolute path>: read it fully, verify the recorded state, then do the next step.`

   ```bash
   python -I ~/.agents/skills/clipboard/scripts/copy.py < "$handoff"
   ```

1. **Confirm**: the saved path, what was copied (full prompt or pointer), and anything still running that the user should know about before clearing.

## Gotchas

- **Authority does not grow**: a handoff records approvals already given; it never turns a proposal into an authorized action.
- **Record staged selections exactly**: the next session must not restage or commit unrelated work.
- **Flag running work for restart**: a background job started by this session may die with it; say whether it must be restarted.

## Documentation

- [Claude Code sessions](https://code.claude.com/docs/en/common-workflows#resume-previous-conversations) · [Codex resume](https://developers.openai.com/codex/cli/reference)
- Companion skills: [task-prompts](../task-prompts/SKILL.md) (prompt grammar and delegation), [clipboard](../clipboard/SKILL.md) (verified copy), [git-worktree](../git-worktree/SKILL.md) (isolated continuation).
