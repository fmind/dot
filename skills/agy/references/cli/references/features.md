# Antigravity Feature Choices

Workstation policy for agy features; consult `antigravity-guide`, `agy --help`, `agy changelog`, or the [sitemap](https://antigravity.google/sitemap.xml) for everything else.

- **Credits stay opt-in**: `/credits` and `useG1Credits` spend post-quota credits (user-enabled only); check plan/cost before `/boost`, `/teamwork`, or `/swarm`.
- **Auto mode reviews nothing here**: `1.5.7+` starts new and headless sessions with no saved mode in `Auto` (`"agentMode": ""` restores `Default`, and `toolPermission: "strict"` overrides Auto/accept-edits); here, `always-proceed` plus `command(*)` in `~/.gemini/config/config.json` still bypass Auto's secondary review, so isolate untrusted repos in a disposable container/VM.
- **`Orchestrator` & `Hydrogen`**: default interactive coding to `Orchestrator` (Carbon plans/reviews read-only, Hydrogen executes; Ultra only, fixed effort) or standalone `Gemini 4 Hydrogen` (`high` default, `xhigh` max) for direct single-model turns (`agy models` lists account IDs; [models](https://antigravity.google/docs/models/)).
- **Per-session `--sandbox`**: restricts terminal commands without replacing a container/VM for untrusted code ([permissions](https://antigravity.google/docs/permissions?tab=cli) vs [sandbox](https://antigravity.google/docs/sandbox/)).
- **`--remote-agent`** (1.5.0+): runs off-machine under `/config`'s `Remote Agent` permissions without local skills; use only on request.
- **ACP server**: `agy acp` (1.5.0+; 1.5.1 exposes all account models; 1.5.4 adds `auto` mode) wires editors via [acp](../../../../agent-protocols/references/acp.md).
- **Subagents over `run_workflow`**: prefer `invoke_subagent` (`Workspace="branch"` or `"share"`, which in 1.5.5+ copy staged, unstaged, and untracked changes up to 100k entries / 4 GiB), `/swarm` for parallel boards, or SDK `asyncio.gather`; reserve `run_workflow` for in-session multi-stage chains.
- **Browser**: `/browser` runs the built-in Chrome subagent; use `chrome-devtools` or `playwright` for scripted/audited runs.
- **Schedules**: `/schedule` manages session timers/crons and `~/.gemini/config/sidecars/<id>/sidecar.json` holds daemon automations; OS jobs belong in [scheduled-jobs](../../../../scheduled-jobs/SKILL.md). Bound `/goal`, `/schedule`, and `/learn` with stop conditions and review persisted output.
- **Recovery**: [continuation](../../../../task-prompts/references/continuation.md) owns resume, `/compact`, and `/fork` (`/resume` never reverts files; inspect rewind before restoring).
- **Rule budgets**: 20,000 tokens (`defaultRulesBudget` in `~/.gemini/config/config.json`) and 24,000 bytes/file, separate from skills/MCP; legacy workflows stopped loading 2026-10-19 (`/migrate-workflows`).
