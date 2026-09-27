---
name: cross-harness-agents
description: Generate reviewer and verifier profiles with Supagents and verify native harness discovery.
---

# Cross-harness agents

`fmind/dot` uses [Supagents](https://github.com/fmind/agent-supagents) to compile two shared roles for Antigravity, Claude Code, Codex, Copilot, Grok, and OpenCode. Each source combines a shared body with explicit native settings. The `AGY` target is separate from Gemini CLI's `GEMINI` target.

## Edit and generate

Work from the chezmoi source repository:

```bash
# Edit dot_agents/supagents/reviewer.md or verifier.md.
mise run agents
mise run check:agents
chezmoi diff --force ~/.claude/agents ~/.codex/agents ~/.copilot/agents ~/.gemini/config/agents ~/.grok/agents ~/.config/opencode/agents
```

`supagents.yaml` maps outputs into chezmoi source paths and stays repository-only. Generated files are tracked and excluded from dprint; edit the canonical source instead. `check:agents` is part of the local/CI gate and rejects changed, missing, or obsolete generated profiles without rewriting files. Preview, then apply only affected targets with `chezmoi apply --force --exclude scripts` so unrelated hooks do not run.

## Roles and invocation

- **reviewer**: inspect supplied changes and surrounding source, rank demonstrated defects, and report evidence and gaps. Supply the diff or its path, relevant files, requirements, and baseline. Some hosts give it no shell, so it cannot obtain Git diffs itself.
- **verifier**: inspect the working-tree boundary, run scoped existing checks, and report commands, exit statuses, failures, and unverified criteria. Mutating checks belong in an isolated candidate containing the relevant uncommitted changes.

Both roles explicitly read the shared persona and applicable repository instructions, avoid implementation and further delegation, and inherit model selection where the host supports it. Omitted model fields use the host's default/inheritance behavior. Always pass task context explicitly; discovery does not imply transcript inheritance or automatic delegation.

| Host        | Personal profile                      | Invoke or inspect                                                  |
| ----------- | ------------------------------------- | ------------------------------------------------------------------ |
| Antigravity | `~/.gemini/config/agents/<role>.md`   | `agy agents`; `agy --agent reviewer`; `/agents`                    |
| Claude Code | `~/.claude/agents/<role>.md`          | `claude --agent reviewer` or `claude --agent verifier`             |
| Codex       | `~/.codex/agents/<role>.toml`         | Ask the parent to use `reviewer` or `verifier` in a new session    |
| Copilot     | `~/.copilot/agents/<role>.agent.md`   | `/agent`; `copilot --agent reviewer`                               |
| Grok        | `~/.grok/agents/<role>.md`            | `grok inspect --json`; `/agents`; `grok --agent reviewer`          |
| OpenCode    | `~/.config/opencode/agents/<role>.md` | `opencode debug agent reviewer`; invoke `@reviewer` or `@verifier` |

Claude's `claude agents` lists background sessions, and version 2.1.283 has removed the `/agents` wizard. Codex's `debug prompt-input` omits custom-role tool schemas, so absence from that dump is not a discovery failure. Parent prompts can request delegation where the host supports custom-agent routing; native invocation syntax and support vary by version.

## Permission limits

Antigravity, Claude, Copilot, Grok, and OpenCode use native tool allowlists or permissions. The reviewer gets file reading/search capabilities; the verifier also gets command execution. Antigravity disables default components and MCP inheritance, and Grok disables MCP inheritance. Codex uses TOML with a `read-only` reviewer sandbox and a `workspace-write` verifier sandbox; parent runtime policy can override these defaults.

These profiles do not establish equivalent sandboxes across harnesses. A verifier's shell can write even without an edit tool. Shared instructions and no-fixes requests describe behavior; they are not operating-system access control. Validate generation, native discovery, and a bounded runtime task separately, including provider availability and effective permissions.

## Compiler maintenance

The dot development dependency pins [Supagents 1.3.0 from PyPI](https://pypi.org/project/supagents/1.3.0/). `dot/uv.lock` records the registry artifacts and their hashes; `uv run --frozen supagents` uses that locked package. CI and fresh checkouts need no vendored wheel or sibling checkout.

To update it, verify the upstream release and PyPI provenance, change the version pin in `dot/pyproject.toml`, then run `uv lock --refresh-package supagents` from the dotfiles root. Run `mise run agents` and the full repository gate on an isolated candidate when unrelated changes are present. Publishing Supagents and adopting its release remain separate delivery steps.
