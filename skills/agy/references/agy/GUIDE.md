---
name: agy
description: "CLI sessions, headless Remote Control, completions, and managed setup."
---

# Antigravity (agy)

Operate the CLI and Remote Control; use [antigravity-sdk](../antigravity-sdk/GUIDE.md) for Python orchestration.

## Workflow

1. Check `agy --version`, `agy --help`, and the relevant subcommand help in the intended workspace. Match CLI, desktop, or IDE documentation to the actual surface.
1. Read the relevant [feature guide](references/features.md) link and [changelog](https://antigravity.google/changelog) before relying on settings, models, or availability. Prefer installed help and built-in `antigravity-guide` / `agy-customizations` for version-specific discovery; report disagreements with web docs.
1. Inspect existing settings, `/skills`, `agy plugin list`, and the requested integration before adding configuration. Reuse working discovery paths; do not duplicate the shared catalog or install plugins speculatively. [agent-project](../../../agent-project/SKILL.md) owns discovery; [mcp-setup](../../../mcp-setup/SKILL.md) owns MCP registration.
1. Use session overrides (`--model`, `--effort`, `--mode`) for task-specific choices; leave saved model and cosmetic preferences to the user. Verify results through artifacts, the native panel, or service status; an allow grant alone does not prove a tool works.

## Managed setup

Edit fmind/dot's chezmoi sources, then preview and apply only affected targets with `chezmoi apply --force`. CLI preferences live in `~/.gemini/antigravity-cli/settings.json`; Remote Control uses `~/.gemini/config/config.json` under `userSettings` with a different protobuf JSON schema. Preserve account fields, trust choices, explicit ask/deny grants, and native model state; never patch `antigravity_state.pbtxt`.

The managed baseline enables Vim with insert-first, notifications, non-workspace access, and Always Proceed. Remote grants allow every action without prompts: `read_file(*)`, `write_file(*)`, `command(*)`, `read_url(*)`, `execute_url(*)`, and `mcp(*)`; explicit ask/deny rules still take precedence. `autoContinueOnMaxGeneratorInvocations` (undocumented, verified in agy 1.2.16) skips the continue prompt after the step budget. `unsandboxed(...)` rules are deprecated on macOS and Linux (current docs keep them for Windows only, and the CLI warns at startup); `command(*)` covers execution inside and outside the sandbox. Keep hooks small: synchronous hooks add latency to the agent loop.

The CLI signs in with the Google account and its plan quota by default; keep it there. Two explicit-only alternatives exist: `"modelProvider": "gemini"` plus an exported `GEMINI_API_KEY` (the only variable read; `.env` files and `GOOGLE_API_KEY` are ignored), or `AGY_ADC_AUTH=true` for ADC against an entitled Google Cloud project. Both bill outside the subscription; never enable either from an ambient key. See [installation and auth](https://antigravity.google/docs/cli/install/) and [enterprise](https://antigravity.google/docs/enterprise/).

## Managed custom agents

Shared roles, such as `code-reviewer`, `security-reviewer`, and `solution-architect`, inherit the session model, support main-agent and subagent use, and list exactly `view_file`, `run_command`, `write_to_file`, `replace_file_content`, `read_url_content`, `search_web`, and `finish`. Verified in agy 1.2.16: omitting `tools` leaves a small read, web, and messaging baseline without shell or edit tools, and an explicit list replaces that baseline (agy always adds `send_message` and `manage_task`). Without `finish`, a `--json-schema` run still exits 0 with `SUCCESS` but omits `structured_output`. Search runs through the shell (`rg`, `fd`), so the legacy `list_dir`, `find_by_name`, and `grep_search` tools, retired from agy's default baseline in 1.2.7, are unnecessary. A misspelled tool name can fail or hang the session; the headless `init.tools` list shows the global registry, not a role's effective tools. Markdown agents inherit ambient skills, rules, and subagents unless `excludeDefaultComponents: true`. Their instructions, not the allowlist, bound actions.

Select with `agy --agent <role>` or `/agents`. For delegation, give the parent the role, scope, acceptance criteria, and relevant diff or evidence paths. Use `agy agents` to verify discovery after applying `~/.gemini/config/agents/` (project roles live in `.agents/agents/`); reopen the panel or start a fresh session to pick up changes.

```bash
agy --agent code-reviewer -i 'Review the working-tree diff. Report verified findings without editing.'
```

That selects the main agent. To spawn subagents, ask the default parent explicitly: “Delegate correctness review to code-reviewer and credential/permission review to security-reviewer. Give each the relevant paths and constraints, have both report without editing, then reconcile findings.” Subagents start with fresh context; include requirements and evidence in the assignment. Use `/agents` to inspect them; `Enter` opens details and `K` terminates a selected subagent. To message an existing subagent, type `@` followed by a space and select it from autocomplete; this differs from `@path` file mentions. [Agents panel](https://antigravity.google/docs/cli/commands/agents/) and the [changelog](https://antigravity.google/docs/changelog) own current controls.

Supagents compiles shared `dot_agents/supagents/` sources into native definitions under `dot_gemini/private_config/agents/`; chezmoi deploys them. Run `mise run agents` after editing a source and `mise run check:agents` to check drift. See [cross-harness agents](../../../agent-project/references/cross-harness-agents.md) for all host mappings and compiler updates. [Custom agents](https://antigravity.google/docs/subagents/) owns the current schema.

## Search, review, and conversation branches

`/codesearch f:hooks.py fullyIdle` searches workspace files directly; it needs no separately configured semantic index. Queries support regex and smart case; `-F` searches literally, `f:<glob>` includes files, and `-f:<glob>` excludes them. Select a match with arrows, press `Enter` to view it or `Ctrl+G` for the external editor, then `C` to comment on a line. Exit with `Esc` and confirm sending to give the agent line-anchored feedback. See [code search](https://antigravity.google/docs/cli/commands/codesearch/).

`/diff` reviews workspace, turn, or commit changes; `Tab` cycles these modes. Open a file with `Enter`, use `N`/`Shift+N` for hunks, and `C` for comments. `/tasks` shows background command logs; `/btw <question>` asks a side question without interrupting the main work. See [diff](https://antigravity.google/docs/cli/commands/diff/) and [CLI reference](https://antigravity.google/docs/cli/reference/).

`/fork` (alias `/branch`) copies the conversation into a new session and switches to it. It does **not** create a Git branch or worktree, and `/resume` returns to another conversation without restoring files. Use it for alternative reasoning; use [git-worktree](../../../git-worktree/SKILL.md) for competing edits, including a snapshot of uncommitted work when needed. Switching the main role in `/agents` also forks an active conversation. `/rewind` has separate recovery controls; inspect the offered operation before restoring anything in a dirty checkout. See [conversations](https://antigravity.google/docs/cli/conversations/).

## Status line and title

The managed CLI settings call [display.py](../../scripts/display.py) with `statusline` or `title`. It runs on Python 3.9 or newer from `PATH`, reads only agy's stdin state JSON, strips incoming terminal controls, and makes no network calls or filesystem reads. The status line uses the terminal's ANSI palette: bold blue project, muted branch (`*` means dirty), activity, full model label (including `Gemini` and `(High)`), execution mode, `context` percentage, task/queued-message/artifact counts, lowest reported remaining quota (`quota min N% left`), and full Vim mode. Context and quota warnings use amber/red plus numeric labels. Optional details drop away on narrow terminals before project/activity text is shortened; missing metrics and zero counts are omitted. `NO_COLOR` or `TERM=dumb` selects plain text. An idle agent with active tasks displays `background`; a pending tool approval displays `needs input`.

The plain title uses `project* — activity · N tasks`, omitting the task count when zero. Neither renderer prints account details, conversation IDs, full paths, or transcript content. `/statusline off` and `/title off` temporarily disable them; applying managed settings enables them again. Follow-up messages queue until the current turn ends by default; agy stores only a non-default `queuedMessages` choice, so it stays host-owned. Native refresh timing and terminal/multiplexer title handling still belong to agy. See [status line](https://antigravity.google/docs/cli/statusline/), [title](https://antigravity.google/docs/cli/title/), and the [queue-setting changelog](https://antigravity.google/docs/changelog).

## Structured headless reviews

Run this from the repository to review, using its existing account and selected model. The [object schema](references/review.schema.json) constrains the report, not tool permissions; the no-edits prompt is an instruction, not filesystem isolation. Use a disposable snapshot for stronger separation from ongoing edits.

```bash
agy --agent code-reviewer --print-timeout 20m --output-format json \
  --json-schema ~/.agents/skills/agy/references/agy/references/review.schema.json \
  -p 'Review the working-tree diff for verified defects. Do not edit files. Return findings, checks actually run, and unresolved gaps.' \
  > /var/tmp/agy-review.json
```

Require a zero process exit code **and** an object `structured_output` before consuming it: on a print timeout agy still reports `status: SUCCESS` and exit 0 with partial output, but omits `structured_output`. Model or agent failures exit 3 with an `AGY_ERROR: {...}` line on stderr; actions refused by permissions are soft-denied, keep exit 0, and appear in `denied_actions`. Since 1.2.14, `--json-schema` accepts only an object-root schema string or file and exits 1 otherwise. Pass `--print-timeout` explicitly: 1.2.6 made the default unlimited although the headless page still says 5 minutes. For several turns in one process, use `--input-format stream-json --output-format stream-json` and read one `result` event per turn; its `usage` is cumulative. A full review of a large working tree took about 15 minutes in testing. Keep results local, choose a distinct output file for concurrent runs, and preserve stderr diagnostics. Record `usage` separately from estimated interactive-session statistics; reported tokens do not establish a monetary charge. See [headless mode](https://antigravity.google/docs/cli/headless/).

This checkout provides `mise run review:agy`. It reviews this repository's working-tree diff, prints the complete JSON envelope including usage, and fails on native CLI errors, malformed JSON, unsuccessful status, or absent structured output. It uses the existing account and selected model; run it manually when a review is useful. It is independent of `all`, commit hooks, and mandatory checks. The no-edits instruction remains a behavioral constraint, not filesystem isolation. `dot` needs no new command for this workflow.

## Headless Remote Control

Use the CLI daemon without installing the desktop app. Read [Remote Control](https://antigravity.google/docs/remote-control/) before changing its persistent OS service. `agy remote-control status` is read-only; `start` registers/restarts and `stop` unregisters it. Restart only when no remote task is running; verify the browser project picker separately.

For one terminal session, `agy --remote-control` or `/remote-control` opens a tunnel that lives only as long as that process and prints a link to the conversation; `/remote-control off` closes it. The daemon is one per machine: a systemd user service `antigravity-cli-daemon` on Linux (`journalctl --user -u antigravity-cli-daemon -n 50`), or since 1.2.14 an unsupervised background process when no systemd user manager exists. `start --name <name>` sets `cliRemoteControlHostname`; `remoteControlHostname` belongs to the desktop app. The browser UI cannot change CLI settings, and the account or organization must have Remote Control enabled.

The daemon reads `~/.gemini/config/config.json` only at start: run `agy remote-control start` after applying changes. Keep the registry local in `~/.gemini/config/projects/`; the [project sync script](../../scripts/sync-projects.py) makes it match the Git checkouts in `~/*/*/.git`:

```bash
python3 ~/.agents/skills/agy/scripts/sync-projects.py          # preview
python3 ~/.agents/skills/agy/scripts/sync-projects.py --apply
```

It adds missing checkouts and removes folder entries outside the glob or duplicated (symlinked checkouts resolve to one entry); entries without folders, such as the native default project, stay. Existing names and metadata are preserved, and new entries are written atomically. This registers projects, not semantic code indexes.

## Shell completions

After upgrades, compare native help with the deployed `~/.config/fish/completions/agy.fish` (chezmoi-managed; edit its source, not the deployed copy). Use a native generator if one becomes available; otherwise maintain this completion and its Carapace exclusion. Verify Fish syntax and representative completions, including `agy mic-serve --` and `agy remote-control st`; `dot completion` refreshes configured generators and caches.

## Official Skills

Use the installed built-in harness guides when available. For product-specific packages, consult [Google's catalog](https://github.com/google/skills) and the [vendor-skill policy](../../../agent-project/references/vendor-skills.md); these do not replace harness guidance.

## Top Links

- [CLI overview](https://antigravity.google/docs/cli/overview/) · [Reference](https://antigravity.google/docs/cli/reference/) · [Feature guide](references/features.md)
- Releases: [Antigravity changelog](https://antigravity.google/changelog)
- [Settings](https://antigravity.google/docs/cli/settings/) · [Permissions](https://antigravity.google/docs/cli/permissions/) · [Troubleshooting](https://antigravity.google/docs/cli/troubleshooting/)
