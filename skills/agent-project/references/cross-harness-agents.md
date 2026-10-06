---
name: cross-harness-agents
description: Generate shared role profiles with Supagents and verify native harness discovery.
---

# Cross-harness agents

`fmind/dot` uses [Supagents](https://github.com/fmind/agent-supagents) to compile shared roles for Antigravity, Claude Code, Codex, Copilot, Grok, and OpenCode. Each source combines a shared body with explicit native settings. The `AGY` target is separate from Gemini CLI's `GEMINI` target.

## Edit and generate

Work from the chezmoi source repository:

```bash
# Edit dot_agents/supagents/<role>.md.
mise run format:agents
mise run check:agents
chezmoi diff --force ~/.claude/agents ~/.codex/agents ~/.copilot/agents ~/.gemini/config/agents ~/.grok/agents ~/.config/opencode/agents
```

`supagents.yaml` maps outputs into chezmoi `exact_agents/` source directories and stays repository-only, so apply removes retired roles and any hand-added profile from those six home directories; keep personal roles in project agent directories. Generated files are tracked and excluded from dprint; edit the canonical source instead. `check:agents` uses Supagents' native strict check to reject warnings and changed, missing, or obsolete generated profiles, and prints content diffs for any drift without writing. `format:agents` runs with `format` and rejects warnings before writing. Preview, then apply only affected targets with `chezmoi apply --force --exclude scripts` so unrelated hooks do not run.

## Roles and invocation

Roles exist for the two delegations that pay off: read-heavy work that would flood the coordinator's context (search, research) and clean-context second opinions (reviews), which avoid the self-preference of reviewing one's own work. Implementation and decisions stay in the coordinator: parallel writers make conflicting implicit choices, and a subagent's summary is lossy, so the coordinator verifies load-bearing claims against the cited evidence before acting ([Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system), [Cognition](https://cognition.com/blog/multi-agents-working)). A role adds a starting skill bundle but never narrows the skill catalog or the main agent's working tools (Antigravity gets them through an explicit allowlist; see [permission limits](#permission-limits)). Every role uses two-part names; add one only after repeated delegations show it pays off.

| Role                | Purpose                                                              | Claude preloads                       |
| ------------------- | -------------------------------------------------------------------- | ------------------------------------- |
| `code-reviewer`     | Correctness, regressions, and data loss in changes                   | repository-review                     |
| `security-reviewer` | Vulnerabilities, secrets, supply chain, agent integrations           | code-security, threat-model           |
| `content-editor`    | Accuracy, clarity, and structure while preserving the author's voice | technical-publishing, repository-docs |
| `deep-researcher`   | Dated, cited briefs from primary sources                             | google-developer                      |

Claude's `skills` field injects those skills when a parent delegates to the role, not when `claude --agent <role>` runs it as the main session; every body also names its starting bundle by path for the other hosts and may load any other catalog skill. Role procedures and output formats are defaults: the task overrides scope, depth, procedure, and format, and blocked steps yield partial results instead of stalls. Reviewers report first and fix only when the task asks; other roles act on the task directly. All roles read the shared persona and applicable repository instructions, may delegate where the host allows nesting, isolate only mutating checks when unrelated edits are present, and inherit model selection where the host supports it. Always pass task context explicitly; discovery does not imply transcript inheritance or automatic delegation.

| Host        | Personal profile                      | Invoke or inspect                                       |
| ----------- | ------------------------------------- | ------------------------------------------------------- |
| Antigravity | `~/.gemini/config/agents/<role>.md`   | `agy agents`; `agy --agent <role>`; `/agents`           |
| Claude Code | `~/.claude/agents/<role>.md`          | `claude --agent <role>`; delegation by name             |
| Codex       | `~/.codex/agents/<role>.toml`         | Ask the parent to use `<role>`                          |
| Copilot     | `~/.copilot/agents/<role>.agent.md`   | `/agent`; `copilot --agent <role>`                      |
| Grok        | `~/.grok/agents/<role>.md`            | `grok inspect --json`; `/agents`; `grok --agent <role>` |
| OpenCode    | `~/.config/opencode/agents/<role>.md` | `opencode debug agent <role>`; invoke `@<role>`         |

Claude's `claude agents` lists background sessions; Claude Code 2.1.198 removed the `/agents` wizard. Codex's `debug prompt-input` omits custom-role tool schemas, so absence from that dump is not a discovery failure. Parent prompts can request delegation where the host supports custom-agent routing; native invocation syntax and support vary by version.

## Permission limits

Roles act. Antigravity is the exception to host defaults: omitting `tools` leaves only a small read, web, and messaging baseline without shell or edit tools, and an explicit list replaces that baseline. Each `AGY` block therefore lists `view_file`, `run_command` (which also covers search through `rg`/`fd`), `write_to_file`, `replace_file_content`, `read_url_content`, `search_web`, and `finish`; without `finish`, `--json-schema` print runs still report `SUCCESS` but omit `structured_output` (verified in agy 1.2.16). The legacy `list_dir`, `find_by_name`, and `grep_search` tools are retired from agy's default baseline and add nothing once the shell is available. Use only names verified at runtime; Antigravity 1.2 rejects an unknown name such as `command_status` before the session starts, and its `skills` field neither preloads nor filters skills. Other hosts receive no tool allowlist, sandbox, or MCP restriction, so their defaults and the parent session's runtime policy apply (Codex inherits the parent sandbox). Shared instructions bound behavior: work within the assigned scope, preserve unrelated work, and require explicit task authority for destructive actions, commits, pushes, publication, production changes, spending, and contacting others. Instructions are not operating-system access control; for an enforced read-only review, run the host in a read-only mode or add a native restriction to that role's target block. Validate generation, native discovery, and a bounded runtime task separately.

## Compiler maintenance

The dot development dependency pins [Supagents from PyPI](https://pypi.org/project/supagents/) exactly in `dot/pyproject.toml`. `dot/uv.lock` records the registry artifacts and their hashes; `uv run --frozen --project dot supagents` uses that locked package. CI and fresh checkouts need no vendored wheel or sibling checkout. Upstream [compatibility evidence](https://github.com/fmind/agent-supagents/blob/main/docs/compatibility.md) distinguishes generated syntax, native discovery, and runtime permissions.

To update it, verify the upstream release and PyPI provenance, change the version pin in `dot/pyproject.toml`, then run `uv lock --project dot --refresh-package supagents` from the dotfiles root. Run `mise run format:agents` and the full repository gate on an isolated candidate when unrelated changes are present. Publishing Supagents and adopting its release remain separate delivery steps.
