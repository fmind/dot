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

In Antigravity, set `subagent: true` (`mainAgent: false` for subagent-only roles), `excludeDefaultComponents: true`, `inheritMcp: false`, and `commandExecutionPolicy: "off"` for read-only reviewers; omitting `tools` leaves a minimal read/web/messaging set, and an explicit list replaces it using registry names from `init.tools` (`view_file`, `list_dir`, `find_by_name`, `grep_search`, `finish`, plus `read_url_content`/`search_web` on `_reviewer_web` only — IDE binds the full read set, whereas `agy` 1.5.x CLI binds `view_file` -> `read_file`, `search_web`, and `finish`, so coordinators pass explicit file lists, diffs, gate logs, and pre-rendered PNG/DOM captures; `skills` neither preloads nor filters). Across Claude, Copilot, and OpenCode, keep all reviewers strictly shell-free and MCP-free (`Bash`/`PowerShell`/`execute`/`shell`, file-edit, delegation, and `"mcp__*"` blocked; `webfetch`/`websearch` restricted to `_reviewer_web` only). Keep `CLAUDE.disallowedTools` to bare tool names + `"mcp__*"` (parameterized `Read(...)` strips `Read` in Claude 2.1.x—enforce path denies in `~/.claude/settings.json` `permissions.deny`), put OpenCode secret denies on `action: read` (`*.env.example` immediately after `*.env*`, relative `.ssh/*` pairs, `external_directory` `/tmp/*` + `/private/tmp/*`, and omit `grep` on `_reviewer_web` since OpenCode `grep` checks patterns rather than paths), and put AGY secret denies in `settings.json`/`config.json` (`read_file(<abs>)`).

Prompt instructions are not OS access control: AGY and Copilot agent frontmatter enforce no per-agent secret-path denies, so untrusted checkouts still require OS sandboxing (`--sandbox --settings '{"allowNonWorkspaceAccess":false}'`) or a disposable snapshot/container/VM (launch `fmind-review-factcheck` from an isolated `/var/tmp/<sandbox>` dir holding sanitized extracts on secret-bearing repos), and you should verify syntax, discovery, and runtime execution separately.
