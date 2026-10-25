---
name: cross-harness-agents
description: "Decide when a custom agent role pays off, write native definitions per host, and verify discovery."
---

# Cross-harness agents

A custom role is a native agent definition: a name, a description, host settings, and a body of instructions. Hosts share no format, so every role is written once per installed host. Prefer the shared persona and skills: a role adds a starting focus, not a capability, and each copy is a maintenance cost.

## When a role pays off

Delegation pays off in two cases: read-heavy work that would flood the coordinator's context (search, research) and clean-context second opinions (reviews), which avoid the self-preference of reviewing one's own work. Implementation and decisions stay in the coordinator: parallel writers make conflicting implicit choices, and a subagent's summary is lossy, so the coordinator verifies load-bearing claims against the cited evidence before acting ([Anthropic](https://www.anthropic.com/research/multi-agent-research-system), [Cognition](https://cognition.com/blog/multi-agents-working)). A host's general-purpose subagent with a task prompt that names the skill to load covers most cases; add a named role only after repeated delegations show the same instructions every time.

## Native definitions

| Host        | Personal profile                      | Project profile                  | Invoke or inspect                               |
| ----------- | ------------------------------------- | -------------------------------- | ----------------------------------------------- |
| Antigravity | `~/.gemini/config/agents/<role>.md`   | `.agents/agents/<role>/agent.md` | `agy agents`; `agy --agent <role>`; `/agents`   |
| Claude Code | `~/.claude/agents/<role>.md`          | `.claude/agents/<role>.md`       | `claude --agent <role>`; delegation by name     |
| Copilot     | `~/.copilot/agents/<role>.agent.md`   | `.github/agents/<role>.agent.md` | `/agent`; `copilot --agent <role>`              |
| OpenCode    | `~/.config/opencode/agents/<role>.md` | `.opencode/agents/<role>.md`     | `opencode debug agent <role>`; invoke `@<role>` |

Every listed host takes YAML frontmatter plus a Markdown body. Claude's `skills` field injects skills when a parent delegates to the role, not when `claude --agent <role>` runs it as the main session, so preload only skills the role always needs. Name conditional skills in the body by path for the other hosts. Inherit model selection where the host supports it, and always pass task context explicitly: discovery does not imply transcript inheritance or automatic delegation.

Claude's `claude agents` lists background sessions, not definitions. Native invocation syntax varies by version; verify with the installed host.

## Permission limits

Antigravity is the exception to host defaults: omitting `tools` leaves a small read, web, and messaging baseline without shell or edit tools, and an explicit list replaces that baseline. A role that must act lists `view_file`, `run_command` (which also covers search through `rg`/`fd`), `write_to_file`, `replace_file_content`, `read_url_content`, `search_web`, and `finish`; without `finish`, `--json-schema` print runs never return `structured_output`. Use only names verified at runtime: Antigravity rejects an unknown name before the session starts, and its `skills` field neither preloads nor filters skills. Other hosts receive no tool allowlist, sandbox, or MCP restriction, so the parent session's runtime policy applies.

Instructions are not operating-system access control. For an enforced read-only review, run the host in a read-only mode or add a native restriction to that role. Validate the definition's syntax, native discovery, and a bounded runtime task separately.
