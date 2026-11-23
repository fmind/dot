---
name: cross-harness-agents
description: "Decide when a custom agent role pays off, write per-host definitions, and verify discovery."
---

# Cross-harness agents

Hosts share no native custom-agent format. Keep content producers dynamic—spawn built-in subagents on demand with the matching [skills](../../skillify/SKILL.md) so the coordinator keeps maximum implementation flexibility. Reserve static named roles compiled via [`supagents`](https://github.com/fmind/agent-supagents) (`.agents/supagents/<role>.md`, or native host files when single-harness) for clean-context, read-only adversarial reviewers ([subagent](../../subagent/SKILL.md); [Anthropic](https://www.anthropic.com/research/multi-agent-research-system), [Cognition](https://cognition.com/blog/multi-agents-working)).

## Native definitions

| Host        | Personal profile                    | Project profile                  | Invoke or inspect                            |
| ----------- | ----------------------------------- | -------------------------------- | -------------------------------------------- |
| Antigravity | `~/.gemini/config/agents/<role>.md` | `.agents/agents/<role>.md`       | `agy agent`; `agy --agent <role>`; `/agents` |
| Copilot     | `~/.copilot/agents/<role>.agent.md` | `.github/agents/<role>.agent.md` | `/agent`; `copilot --agent <role>`           |

Both use YAML frontmatter + Markdown body (Antigravity also discovers `.agents/agents/<role>/agent.md`). Inherit the model where supported and pass task context explicitly.

## Permission limits

- **Shared `agy-secret-denies.tmpl`**: defines the credential paths (incl. `~/.local/share/atuin`, `~/.cache/huggingface/stored_tokens`, `.private.fish`, `.pgpass`) and secret globs (`*.env*`, `*.pem`, `*.key`, `*.p12`, `*.pfx`) enforced by managed Antigravity configs. Copilot (`COPILOT_ALLOW_ALL=1`) enforces no secret-read denies globally or per agent.
- **Antigravity (`agy`)**:
  - Set `subagent: true` (`mainAgent: false` if subagent-only), `excludeDefaultComponents: true`, `inheritMcp: false` (and `inheritCustomizations: false` when isolating plugin/workspace rules/skills), and `commandExecutionPolicy: "off"` for read-only reviewers.
  - Omitting `tools` leaves a minimal read/web/messaging set. An explicit list replaces it from `init.tools`: `view_file`, `list_dir`, `find_by_name`, `grep_search`, `finish`, plus `read_url_content`/`search_web` on `_reviewer_web` (known issue: unmapped or misspelled tool names can hang the subagent).
  - IDE binds the full read set; `agy` 1.5.x CLI binds `view_file` -> `read_file`, `search_web`, `finish`. Pass file lists, diffs, gate logs, and PNG/DOM captures; `skills` neither preloads nor filters.
  - Enforce shared denies via `read_file(<abs>)` (recursive for directories) and `read_file(<glob>)` in `settings.json` and `config.json`.
- **Copilot**:
  - Restrict `tools` to `[read, search]` on `_reviewer` and `[read, search, web]` on `_reviewer_web`; omit `execute`, `edit`, `agent`, and MCP tool globs.
- **OS isolation**: Prompt rules are not OS controls. Antigravity (`agy`) and Copilot frontmatter enforce no per-agent path denies, so untrusted repos need `--sandbox --settings '{"allowNonWorkspaceAccess":false}'` or a disposable VM/container. Launch `fmind-review-factcheck` from `/var/tmp/<sandbox>` holding sanitized extracts on secret-bearing repos; verify syntax, discovery, and execution separately.
