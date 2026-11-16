---
name: cross-harness-agents
description: "Decide when a custom agent role pays off, write per-host definitions, and verify discovery."
---

# Cross-harness agents

Hosts share no native custom-agent format. Keep content producers dynamic—spawn built-in subagents on demand with the matching [skills](../../skillify/SKILL.md) so the coordinator keeps maximum implementation flexibility. Reserve static named roles compiled via [`supagents`](https://github.com/fmind/agent-supagents) (`.agents/supagents/<role>.md`, or native host files when single-harness) for clean-context, read-only adversarial reviewers ([subagent](../../subagent/SKILL.md); [Anthropic](https://www.anthropic.com/research/multi-agent-research-system), [Cognition](https://cognition.com/blog/multi-agents-working)).

## Native definitions

| Host        | Personal profile                      | Project profile                  | Invoke or inspect                                      |
| ----------- | ------------------------------------- | -------------------------------- | ------------------------------------------------------ |
| Antigravity | `~/.gemini/config/agents/<role>.md`   | `.agents/agents/<role>.md`       | `agy agent`; `agy --agent <role>`; `/agents`           |
| Claude Code | `~/.claude/agents/<role>.md`          | `.claude/agents/<role>.md`       | `claude --agent <role>`; delegation by name            |
| Copilot     | `~/.copilot/agents/<role>.agent.md`   | `.github/agents/<role>.agent.md` | `/agent`; `copilot --agent <role>`                     |
| OpenCode    | `~/.config/opencode/agents/<role>.md` | `.opencode/agents/<role>.md`     | `opencode debug agents --standalone`; delegate by name |

All four use YAML frontmatter + Markdown body (Antigravity also discovers `.agents/agents/<role>/agent.md`; Codex uses `.codex/agents/<role>.toml`; Pi uses TypeScript extensions rather than role files). Claude's `skills` preloads only on subagent delegation (not `claude --agent <role>`), and `claude agents` lists background sessions rather than roles. Inherit the model where supported and pass task context explicitly.

## Permission limits

In Antigravity, set `subagent: true` (`mainAgent: false` for subagent-only roles); omitting `tools` leaves a minimal read/web/messaging set without shell or edit, and an explicit list replaces it: use exact registry names from `init.tools` (`view_file`, `grep_search`, `run_command`, `write_to_file`, `replace_file_content`, `read_url_content`, `search_web`, and `finish` for `--json-schema` `structured_output` — never model-prompt aliases like `read_file`/`edit_file`, as unmapped names fail or hang startup), and note `skills` neither preloads nor filters. Other hosts inherit the parent session's permissions.

Instructions are not OS access control: enforce read-only reviews via host read-only mode or native role restrictions, and test syntax, discovery, and runtime execution separately.
