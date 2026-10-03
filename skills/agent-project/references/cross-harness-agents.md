---
name: cross-harness-agents
description: Generate reviewer and security-reviewer profiles with Supagents and verify native harness discovery.
---

# Cross-harness agents

`fmind/dot` uses [Supagents](https://github.com/fmind/agent-supagents) to compile two shared roles for Antigravity, Claude Code, Codex, Copilot, Grok, and OpenCode. Each source combines a shared body with explicit native settings. The `AGY` target is separate from Gemini CLI's `GEMINI` target.

## Edit and generate

Work from the chezmoi source repository:

```bash
# Edit dot_agents/supagents/reviewer.md or security-reviewer.md.
mise run agents:diff
mise run agents
mise run check:agents
chezmoi diff --force ~/.claude/agents ~/.codex/agents ~/.copilot/agents ~/.gemini/config/agents ~/.grok/agents ~/.config/opencode/agents
```

`supagents.yaml` maps outputs into chezmoi source paths and stays repository-only. Generated files are tracked and excluded from dprint; edit the canonical source instead. `agents:diff` shows source-to-output mappings and content diffs without writing; it exits 1 when drift exists. `check:agents` uses Supagents' native strict check to reject warnings and changed, missing, or obsolete generated profiles. `agents` rejects warnings before writing. Preview, then apply only affected targets with `chezmoi apply --force --exclude scripts` so unrelated hooks do not run.

## Roles and invocation

- **reviewer**: inspect supplied changes and surrounding source, rank demonstrated defects, and report evidence and gaps. Supply the diff or its path, relevant files, requirements, and baseline. Some hosts give it no shell, so it cannot obtain Git diffs itself.
- **security-reviewer**: trace attacker-controlled inputs, run the repository's read-only security scanners, and report verified vulnerabilities with proof boundaries and coverage gaps. It routes through `security-review`, `threat-model`, `ai-security-assessment`, and `skill-security-review`; Claude preloads the first two.

Roles exist to equip a persona with skills and least-privilege tools; repository checks run in the coordinator. Claude's `skills` field preloads skill content at startup; other hosts follow the body's skill paths.

Both roles explicitly read the shared persona and applicable repository instructions, avoid implementation and further delegation, and inherit model selection where the host supports it. Omitted model fields use the host's default/inheritance behavior. Always pass task context explicitly; discovery does not imply transcript inheritance or automatic delegation.

| Host        | Personal profile                      | Invoke or inspect                                                           |
| ----------- | ------------------------------------- | --------------------------------------------------------------------------- |
| Antigravity | `~/.gemini/config/agents/<role>.md`   | `agy agents`; `agy --agent reviewer`; `/agents`                             |
| Claude Code | `~/.claude/agents/<role>.md`          | `claude --agent reviewer` or `claude --agent security-reviewer`             |
| Codex       | `~/.codex/agents/<role>.toml`         | Ask the parent to use `reviewer` or `security-reviewer`                     |
| Copilot     | `~/.copilot/agents/<role>.agent.md`   | `/agent`; `copilot --agent reviewer`                                        |
| Grok        | `~/.grok/agents/<role>.md`            | `grok inspect --json`; `/agents`; `grok --agent reviewer`                   |
| OpenCode    | `~/.config/opencode/agents/<role>.md` | `opencode debug agent reviewer`; invoke `@reviewer` or `@security-reviewer` |

Claude's `claude agents` lists background sessions; Claude Code 2.1.198 removed the `/agents` wizard. Codex's `debug prompt-input` omits custom-role tool schemas, so absence from that dump is not a discovery failure. Parent prompts can request delegation where the host supports custom-agent routing; native invocation syntax and support vary by version.

## Permission limits

Antigravity, Claude, Copilot, Grok, and OpenCode use native tool allowlists or permissions. The reviewer gets file reading/search capabilities; the security reviewer also gets command execution for scanners. Antigravity disables default components and MCP inheritance, and Grok disables MCP inheritance. Codex uses TOML with a `read-only` reviewer sandbox and a `workspace-write` security-reviewer sandbox, which blocks network by default, so advisory-database scans report coverage gaps there; parent runtime policy can override these defaults.

These profiles do not establish equivalent sandboxes across harnesses. The security reviewer's shell can write even without an edit tool. Shared instructions and no-fixes requests describe behavior; they are not operating-system access control. Validate generation, native discovery, and a bounded runtime task separately, including provider availability and effective permissions.

## Compiler maintenance

The dot development dependency pins [Supagents 1.4.0 from PyPI](https://pypi.org/project/supagents/1.4.0/). `dot/uv.lock` records the registry artifacts and their hashes; `uv run --frozen supagents` uses that locked package. CI and fresh checkouts need no vendored wheel or sibling checkout. Upstream [compatibility evidence](https://github.com/fmind/agent-supagents/blob/main/docs/compatibility.md) distinguishes generated syntax, native discovery, and runtime permissions.

To update it, verify the upstream release and PyPI provenance, change the version pin in `dot/pyproject.toml`, then run `uv lock --refresh-package supagents` from the dotfiles root. Run `mise run agents` and the full repository gate on an isolated candidate when unrelated changes are present. Publishing Supagents and adopting its release remain separate delivery steps.
