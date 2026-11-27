# Antigravity Feature Choices

Workstation policy for `agy`; use `agy --help`, `agy changelog`, or [docs index](https://antigravity.google/llms.txt) (`.md`) for reference.

## Modes, Sandboxing & Cost

- **Credits stay opt-in**: `/credits` and `useG1Credits` spend post-quota credits (hidden on business/API-key sessions); check cost before `/boost`, `/teamwork`, or `/swarm`.
- **`Auto` vs managed `always-proceed`**:
  - New/headless sessions default to `Auto` (`"agentMode": ""` restores `Default`; `toolPermission: "strict"` overrides `Auto`/`accept-edits`).
  - In `agy 1.5.16+`, `Auto` permits non-workspace reads plus outside-workspace VCS edits and additive-only writes without asking (overwrites outside VCS, hidden/VCS/hook metadata, and `ask`/`deny` still apply); pass `--sandbox --settings '{"allowNonWorkspaceAccess":false}'` to block non-workspace access.
  - Shell expansion (`$(...)`, backticks, `<(...)`, `{a,b}`) and flags (`git -c ...`) disable prefix matching; use exact/regex rules.
  - Managed `always-proceed` + `command(*)` in `config.json` override `Auto` and disable OS sandboxing (`read_file(...)` denies never block shell); isolate untrusted repos in a container/VM.
- **Per-session `--sandbox`**: confines shell commands (blocks `~/.config` and `~/.git-credentials`, enforces `permissions.deny` at mount level; `sandboxProxy.http` pairs `address`+`certFile` and must enforce `read_url`; [sandbox](https://antigravity.google/docs/sandbox/)).
- **`--remote-agent`**: off-machine (`default`/`accept-edits`/`plan`; exits `2` under `GEMINI_API_KEY`) via `/projects` and OAuth plugins, excluding `-p`, `/codesearch`, `/diff`, `/fork`, `/rewind`, `/btw`, `/voice`, `!`, `@` subagents, and local MCP/plugins/skills; opt-in only.

## Models, TUI & Voice

- **Models**: prefer **`Orchestrator (Neon)`** (`gemini-pro-orchestrator-neon`, planning on Neon and executing/subagents on Hydrogen) or **`Gemini 4 Neon (Medium)`** with `verbosity: "medium"` for daily work; reserve `Neon (High)`/`(XHigh)` for hard debugging or architecture. `Gemini 4 Neon` has a 512K context (`Neon`/`Hydrogen` add `xhigh`; `GPT-OSS-120b` retires 2026-11-30). Check IDs via `agy models`, one-shot via `/model <model> <prompt>`, effort via `agy -p "/effort"` ([models](https://antigravity.google/docs/models/)).
- **`Orchestrator`**: IDs are `gemini-pro-orchestrator-neon`, `gemini-pro-orchestrator` (Carbon), `gemini-pro-orchestrator-argon`. Pro/Ultra `/model` sets `Planner` (`Neon`/`Carbon`/`Argon`/`Claude Opus 5.5`), `Executor` (`Hydrogen`/`Claude Sonnet 5.5`), and per-role `Effort` (`"orchestrator"`; `/effort` ignored); Enterprise/`AGY_ADC_AUTH` fix Carbon + Hydrogen High.
- **Display, voice & ACP**: `/thinking [on|off]` (`"showThinking"`) streams thoughts; `altScreenMode` `"always"` adds table copy, `"never"` stays inline ([managed setup](../GUIDE.md#managed-setup); `Ctrl+K` approves subagents). `/voice` (`F5`–`F7`) needs personal sessions—over SSH, tunnel `agy mic-serve` (`127.0.0.1:4713`) via `ANTIGRAVITY_MIC` ([voice](https://antigravity.google/docs/cli/commands/voice/)). `agy acp` exposes ACP ([acp](../../../../agent-frameworks/references/acp.md)).

## Multi-Agent, Automation & Budgets

- **Subagents & workflows**: prefer `invoke_subagent` (`Workspace="branch"|"share"`, 100k entries / 4 GiB, depth 10) or SDK `asyncio.gather`. Reserve `run_workflow` (`ANTIGRAVITY_PYTHON` >=3.8; `Ctrl+T`/`/tasks`) for scripted fan-out; `/swarm` is user-only (`Alt+S`).
- **Browser, schedules & budgets**: `/browser` drives Chrome in CLI ([web-frontend](../../../../web-frontend/SKILL.md)). `/schedule` owns session timers, `~/.gemini/config/sidecars/` owns App sidecars, [scheduled-jobs](../../../../dot-cli/references/scheduled-jobs/GUIDE.md) owns OS jobs; bound `/goal`, `/schedule`, `/learn`. [continuation](../../task-prompts/references/continuation.md) owns `/resume`/`/compact`/`/fork`; rule budgets: 20k tokens (`defaultRulesBudget`) and 24 KB/file after `@[label](path)` inlines.
