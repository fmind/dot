---
name: cross-harness-agents
description: "Decide when a custom agent role pays off, write per-host definitions, and verify discovery."
---

# Cross-harness agents

Hosts share no custom-agent format, so each role must be maintained per host. Prefer the shared persona plus skills—add a named role only after repeated delegations reuse identical instructions.

## When a role pays off

Delegate only for context-heavy read/search work or clean-context reviews that avoid self-preference; keep edits and decisions in the coordinator, verifying load-bearing subagent claims against cited evidence ([Anthropic](https://www.anthropic.com/research/multi-agent-research-system), [Cognition](https://cognition.com/blog/multi-agents-working)). A general-purpose subagent prompted with the skill to load suffices in most cases.

## Native definitions

| Host        | Personal profile                      | Project profile                  | Invoke or inspect                            |
| ----------- | ------------------------------------- | -------------------------------- | -------------------------------------------- |
| Antigravity | `~/.gemini/config/agents/<role>.md`   | `.agents/agents/<role>/agent.md` | `agy agent`; `agy --agent <role>`; `/agents` |
| Claude Code | `~/.claude/agents/<role>.md`          | `.claude/agents/<role>.md`       | `claude --agent <role>`; delegation by name  |
| Copilot     | `~/.copilot/agents/<role>.agent.md`   | `.github/agents/<role>.agent.md` | `/agent`; `copilot --agent <role>`           |
| OpenCode    | `~/.config/opencode/agents/<role>.md` | `.opencode/agents/<role>.md`     | `opencode debug agents`; delegation by name  |

All four use YAML frontmatter + Markdown body (Pi uses TypeScript extensions and prompt templates rather than custom-agent role files). Claude's `skills` preloads only on subagent delegation (not `claude --agent <role>`), so preload only always-needed skills and cite conditional skills by path; `claude agents` lists background sessions, not roles. Inherit the model where supported and pass task context explicitly.

## Permission limits

In Antigravity, omitting `tools` leaves a minimal read/web/messaging set without shell or edit, and an explicit list replaces it: include `view_file`, `run_command`, `write_to_file`, `replace_file_content`, `read_url_content`, `search_web`, and `finish` (required for `--json-schema` `structured_output`); unknown tool names fail startup, and `skills` neither preloads nor filters. Other hosts inherit the parent session's permissions.

Instructions are not OS access control: enforce read-only reviews via host read-only mode or native role restrictions, and test syntax, discovery, and runtime execution separately.
