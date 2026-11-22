# Antigravity Feature Choices

Workstation policy for `agy` features; consult `antigravity-guide`, `agy --help`, `agy changelog`, or the [docs index](https://antigravity.google/llms.txt) (append `.md` to any docs page) for everything else.

## Modes, Sandboxing & Cost

- **Credits stay opt-in**: `/credits` and `useG1Credits` spend post-quota credits (user-enabled only); check plan/cost before `/boost`, `/teamwork`, or user-invoked `/swarm`.
- **`Auto` vs managed `always-proceed`**: new/headless sessions default to `Auto` (`"agentMode": ""` restores `Default`; `toolPermission: "strict"` overrides Auto/accept-edits; `Auto` allows non-workspace reads without prompting while writes/denies still apply). Here, managed `always-proceed` + `command(*)` in `~/.gemini/config/config.json` override `Auto` and disable the OS sandbox (`read_file(...)` denies do not block shell commands); isolate untrusted repos in a container/VM.
- **Per-session `--sandbox`**: restricts terminal commands without replacing a container/VM for untrusted code (blocks `~/.config` and `~/.git-credentials` by default while enforcing `permissions.deny` at OS mount level; [permissions](https://antigravity.google/docs/permissions?tab=cli) vs [sandbox](https://antigravity.google/docs/sandbox/)).
- **`--remote-agent`**: runs off-machine under `/config` → `Remote Agent` without local skills (`default`, `accept-edits`, `plan`; exits `2` under `GEMINI_API_KEY`); use only on request.

## Models, TUI & Voice

- **`Orchestrator`, `Neon`, & `Hydrogen`**: on Pro/Ultra local sessions, `/model`'s `Orchestrator` row configures `Planner` (`Neon`, `Carbon`, `Argon`, `Claude Opus 5.5`), `Executor` (`Hydrogen`, `Claude Sonnet 5.5`), and per-role `Effort` (`Tab`/`Shift+Tab`, `←`/`→`; saved under `"orchestrator"` in `settings.json`; `/effort` does not apply directly). Enterprise and `AGY_ADC_AUTH` stay fixed to Carbon + Hydrogen High (`--model gemini-pro-orchestrator`). Use `/model <model> <prompt>` for one-shot turns (`agy models` lists IDs; [models](https://antigravity.google/docs/models/)).
- **Display & shortcuts**: `/thinking [on|off]` (`"showThinking"` in `settings.json`) streams thoughts live without `Ctrl+O`. `altScreenMode: "always"` adds click-to-expand, scroll indicator, and column-aware Markdown table copy (trading native scrollback). See [managed setup](../GUIDE.md#managed-setup) for Zellij-safe shortcuts (`Ctrl+K` fast-approves subagent prompts).
- **Voice & SSH**: `/voice live` (`F6`) and `/voice dictate` or `/record` (`F5`) work on personal interactive sessions (disabled under `GEMINI_API_KEY` and business/enterprise); tunnel `agy mic-serve` (`127.0.0.1:4713`) over reverse SSH for remote hosts ([voice](https://antigravity.google/docs/cli/commands/voice/)).
- **ACP server**: `agy acp` exposes account models, `auto` mode, and context-window updates; wire editors via [acp](../../../../agent-frameworks/references/acp.md).

## Multi-Agent, Automation & Budgets

- **Subagents, `run_workflow`, & `/swarm`**: prefer `invoke_subagent` (`Workspace="branch"` or `"share"`, copying staged/unstaged/untracked changes up to 100k entries / 4 GiB) or SDK `asyncio.gather`. Reserve `run_workflow` (override bundled Python via `ANTIGRAVITY_PYTHON`) for scripted multi-stage fan-out. User-only `/swarm` coordinates peers on `/swarm board` (`Alt+S`, `Alt+X` dismiss; live `Overview` header shows up to 6 workstreams on `>= 28`-row terminals).
- **Browser & schedules**: `/browser` runs built-in Chrome; use [web-frontend](../../../../web-frontend/SKILL.md) for audited runs. `/schedule` manages session timers/crons (`~/.gemini/config/sidecars/<id>/sidecar.json` for daemons); OS jobs live in [scheduled-jobs](../../../../dot-cli/references/scheduled-jobs/GUIDE.md). Bound `/goal`, `/schedule`, and `/learn` with stop conditions and review persisted output.
- **Recovery & rule budgets**: [continuation](../../task-prompts/references/continuation.md) owns `/resume`, `/compact`, and `/fork` (`/resume` never reverts files; inspect rewind first). Rule budgets: 20,000 tokens (`defaultRulesBudget`) and 24,000 bytes/file, separate from skills/MCP; legacy workflows stopped loading (`/migrate-workflows`).
