---
name: deleguate-tasks
description: Delegate and track tasks through a chosen external harness. Use only when the user explicitly requests delegation, such as "Deleguate these tasks to agy" or /deleguate-tasks.
disable-model-invocation: true
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/deleguate-tasks
  created: "2026-09-16"
  updated: "2026-09-16"
---

# Deleguate Tasks

Keep the current agent as coordinator and offload bounded work to the user's chosen harness, returning compact evidence instead of entire worker transcripts.

## Invocation and defaults

- Run only after an explicit user request to delegate; ordinary implementation, review, or cost-reduction requests do not activate this workflow. Creating or discussing this skill does not authorize launching workers.
- Preserve the requested spelling: `/deleguate-tasks` in Claude, `$deleguate-tasks` in Codex, or an explicit natural-language delegation request where the host supports it. With implicit discovery disabled, use the named invocation if a host does not resolve the natural request.
- Default to `agy`, model `gemini-3.8-flash-high` (Gemini 3.8 Flash High), effort `high`. User-selected harness, model, effort, and concurrency override these defaults; the Gemini default applies only to agy.
- Start with one active worker. For an explicit multi-task delegation, run up to two independent tasks concurrently when their workspace ownership is isolated; respect any user-specified limit. Run dependencies in order.
- Use the harness's native CLI and existing authenticated account. Do not silently switch harnesses, models, API billing, credit fallback, or permission policies when blocked.

## Workflow

1. **Resolve the request**: identify the tasks, allowed changes, workspace, dependencies, and acceptance criteria. For a bare invocation with no task context, ask for the tasks. Read the selected harness skill: [agy](../agy/SKILL.md), [Claude](../claude/SKILL.md), or [Codex](../codex/SKILL.md); use its installed help and current official guidance for execution and resume syntax. For another harness, locate its owning skill rather than reusing agy flags.
1. **Prepare bounded briefs**: send each worker its objective, relevant paths, project instructions, authorized actions, acceptance checks, and required return format. Use [agent-prompt](../agent-prompt/SKILL.md) when a detailed handoff is needed. Include a prohibition on further delegation unless the user authorized it. Send references and necessary context, not the parent's full conversation.
1. **Assign workspaces**: inspect existing changes before launching writers. Serialize shared-workspace edits; use [git-worktree](../git-worktree/SKILL.md) for concurrent writers or an exact dirty candidate. A clean worktree does not include uncommitted user changes. Record the tested starting revision and relevant dirty snapshot. A worktree isolates edits, not credentials or permissions.
1. **Create the ledger**: use [tracking and execution](references/tracking.md) before starting processes. Keep one coordinator as the ledger writer, one stable ID per task, and distinct attempt files. Store briefs, raw output, and diagnostics outside the repository by default.
1. **Launch and monitor**: invoke the external CLI directly through the host's process tool; do not spend a native model subagent merely to wait on another harness. Capture the process handle immediately, then the native conversation ID when available. Keep the user informed of meaningful results while other independent work proceeds. Bound runtime and explicitly record permission denials, authentication failures, and quota failures.
1. **Resume deliberately**: continue a task by its recorded conversation ID, never by a shared "latest conversation" selector. Inspect workspace and process state before retrying; do not duplicate a still-running task. On user stop, cancel active owned processes, prevent queued tasks and retries from starting, and record their states.
1. **Verify and integrate**: a successful process or worker assertion is not acceptance. Review the returned artifacts and diff, run acceptance checks appropriate to the task, and integrate only authorized changes. Keep full transcripts out of the parent context; read relevant excerpts when needed. Mark a task complete only after coordinator verification.
1. **Report and clean up**: report each task's outcome, changed files, checks, blockers, and ledger location. Confirm workers have exited before removing task-owned disposable workspaces. Retain the compact ledger and useful results for continuation; delete redundant scratch data after recording its disposition. Never delete unintegrated work or user data.

## Documentation

- [Tracking and execution](references/tracking.md): local ledger, worker return contract, agy invocation, and failure handling.
- [Batch execution helper](scripts/run.py): executes bounded task batches and keeps worker transcripts outside coordinator context.
- [Codex invocation policy](agents/openai.yaml) disables implicit selection; Claude's frontmatter does the same. These controls govern skill selection, not subprocess permissions.
- [Antigravity headless mode](https://antigravity.google/docs/cli/headless/) · [Claude skill invocation](https://code.claude.com/docs/en/skills) · [Codex skills](https://learn.chatgpt.com/docs/build-skills).
- Releases: [Antigravity](https://antigravity.google/changelog). The selected harness skill owns its evolving command and authentication details.
