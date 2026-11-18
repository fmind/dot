---
name: cross-harness-agents
description: "Decide when a custom agent role pays off, write per-host definitions, and verify discovery."
---

# Cross-harness agents

Hosts share no native custom-agent format. Keep content producers dynamic—spawn built-in subagents on demand with the matching [skills](../../skillify/SKILL.md) so the coordinator keeps maximum implementation flexibility. Reserve static named roles compiled via [`supagents`](https://github.com/fmind/agent-supagents) (`.agents/supagents/<role>.md`, or native host files when single-harness) for clean-context, read-only adversarial reviewers ([subagent](../../subagent/SKILL.md); [Anthropic](https://www.anthropic.com/research/multi-agent-research-system), [Cognition](https://cognition.com/blog/multi-agents-working)).

## Native definitions

| Host        | Personal profile                      | Project profile                  | Invoke or inspect                                                   |
| ----------- | ------------------------------------- | -------------------------------- | ------------------------------------------------------------------- |
| Antigravity | `~/.gemini/config/agents/<role>.md`   | `.agents/agents/<role>.md`       | `agy agent`; `agy --agent <role>`; `/agents`                        |
| Claude Code | `~/.claude/agents/<role>.md`          | `.claude/agents/<role>.md`       | `claude --agent <role>`; delegation by name                         |
| Copilot     | `~/.copilot/agents/<role>.agent.md`   | `.github/agents/<role>.agent.md` | `/agent`; `copilot --agent <role>`                                  |
| OpenCode    | `~/.config/opencode/agents/<role>.md` | `.opencode/agents/<role>.md`     | `opencode debug agents --standalone`; `opencode run --agent <role>` |

All four use YAML frontmatter + Markdown body (Antigravity also discovers `.agents/agents/<role>/agent.md`; Codex uses `.codex/agents/<role>.toml`; Pi uses TypeScript extensions rather than role files). Claude's `skills` preloads only on subagent delegation (not `claude --agent <role>`), and `claude agents` lists background sessions rather than roles. Inherit the model where supported and pass task context explicitly.

## Permission limits

In Antigravity, set `subagent: true` (`mainAgent: false` for subagent-only roles); omitting `tools` leaves a minimal read/web/messaging set without shell or edit, and an explicit list replaces it: use exact registry names from `init.tools` (`view_file`, `list_dir`, `find_by_name`, `grep_search`, `run_command`, `write_to_file`, `replace_file_content`, `read_url_content`, `search_web`, and `finish` for `--json-schema` `structured_output` — IDE binds the full read set, whereas `agy` 1.5.x CLI binds `view_file` -> `read_file`, `run_command`, `search_web`, and `finish`, so reviewer roles include `run_command` with `commandExecutionPolicy: sandbox` while omitting `write_to_file`/`replace_file_content`/`invoke_subagent`), and note `skills` neither preloads nor filters. In Claude, Copilot, and OpenCode, strip file-edit (`Write`/`Edit`/`edit`) and subagent-delegation tools (plus live authenticated browser tools such as `mcp__claude-in-chrome__*`) while retaining non-mutating shell + headless Chrome/Playwright inspection (`external_directory` `/tmp/*` and `/private/tmp/*` in OpenCode v2 so `/tmp` renders stay readable).

Prompt instructions are not OS access control: native reviewer role files strip structured file-edit and delegation tools while leaving diagnostic shell enabled, so untrusted checkouts still require OS sandboxing (`--sandbox --settings '{"allowNonWorkspaceAccess":false}'`) or a disposable snapshot/container/VM, and you should verify syntax, discovery, and runtime execution separately.
