---
name: cross-harness-agents
description: "Decide when a custom agent role pays off, write per-host definitions, and verify discovery."
---

# Cross-harness agents

Hosts share no native custom-agent format. Keep content producers dynamic—spawn built-in subagents on demand with the matching [skills](../../skillify/SKILL.md) so the coordinator keeps maximum implementation flexibility. Reserve static named roles compiled via [`supagents`](https://github.com/fmind/agent-supagents) (`.agents/supagents/<role>.md`, or native host files when single-harness) for clean-context, read-only adversarial reviewers ([subagent](../../subagent/SKILL.md); [Anthropic](https://www.anthropic.com/research/multi-agent-research-system), [Cognition](https://cognition.com/blog/multi-agents-working)).

## Native definitions

| Host        | Personal profile                    | Project profile                  | Invoke or inspect                                          |
| ----------- | ----------------------------------- | -------------------------------- | ---------------------------------------------------------- |
| Antigravity | `~/.gemini/config/agents/<role>.md` | `.agents/agents/<role>.md`       | `agy agent` (global only); `agy --agent <role>`; `/agents` |
| Copilot     | `~/.copilot/agents/<role>.agent.md` | `.github/agents/<role>.agent.md` | `/agent`; `copilot --agent <role>`                         |

Both use YAML frontmatter + Markdown body (Antigravity also discovers `.agents/agents/<role>/agent.md`; `agy agent` lists global/personal agents only, so verify project `.agents/agents/` via `/agents` or `agy --agent <role>`). Route `agy` reviewers via `model: flash` (`Gemini 4 Hydrogen (High)`) or inherit where supported, and pass task context explicitly.

## Permission limits

- **Shared `agy-secret-denies.tmpl`**: defines `$HOME` credential/history/config paths (incl. `~/.local/share/atuin`, `~/.local/share/fish/fish_history`, `~/.local/share/keyrings`, `~/.config/dot.yaml`, `~/.config/git/config.local`, `~/.agentsview`, `~/.private.fish`, `~/.pgpass`), workspace-root secret filenames (`.env`, `.env.local`, `.env.production`, `id_ed25519`, `application_default_credentials.json`), and cloud-metadata `read_url`/`execute_url` SSRF denies (`169.254.169.254`, `metadata.google.internal`, `metadata.goog`, `100.100.100.200`, `[fd00:ec2::254]`). **Quirk (`agy` 1.5.16)**: `read_file(...)` matches exact paths and recursive absolute directories (canonicalizing symlinks), **not** wildcard globs (`*.env*`/`**/*.env*` are silent no-ops), and relative filenames match workspace root only. Copilot (`COPILOT_ALLOW_ALL=1`) enforces no secret-read denies globally or per agent.
- **Antigravity (`agy`)**:
  - Set `subagent: true` (`mainAgent: false` if subagent-only), `model: flash`, `excludeDefaultComponents: true`, `inheritCustomizations: false`, `inheritMcp: false`, and `commandExecutionPolicy: "off"` for read-only reviewers.
  - **Frontmatter `model:` tiers (`agy` 1.5.17)**:
    - Custom `.md` profiles accept **only** `inherit`, `flash`, `flash_lite`, and `pro` (literal model IDs like `gemini-4-hydrogen-medium` or display names are silently dropped at discovery; `effort:` is silently ignored).
    - In `invoke_subagent`, `flash` resolves to `Gemini 4 Hydrogen (High)`, `pro` to `Gemini 4 Hydrogen (XHigh)`, `flash_lite` to `Gemini 3.5 Flash Lite`, and `inherit` to the parent model (or `Hydrogen High` under `Orchestrator`). Explicit `model: inherit` blocks caller `Model="flash"`; omit `model:` to allow per-call overrides.
    - Top-level `agy --agent <role>` ignores frontmatter `model:` and requires `--model` (e.g., `--model gemini-4-hydrogen-medium`).
  - Omitting `tools` leaves a minimal read/web/messaging set. An explicit list replaces it from `init.tools`: `view_file`, `list_dir`, `find_by_name`, `grep_search`, `finish`, plus `read_url_content`/`search_web` on `_reviewer_web` (known issue: unmapped or misspelled tool names can hang the subagent).
  - IDE binds the full read set; `agy` 1.5.x CLI binds `view_file` -> `read_file`, `finish`, and auto-added `manage_task`/`send_message` (plus `search_web` on `_reviewer_web`, never `read_url_content`/`list_dir`/`grep_search`). Because `excludeDefaultComponents: true` strips workspace CWD, **always pass absolute paths** plus pre-captured diffs, file manifests, gate logs, and PNG/DOM renders; `skills` neither preloads nor filters.
  - Enforce shared denies in `settings.json` and `config.json` (denying `read_file` also denies `write_file`).
- **Copilot**:
  - Restrict `tools` to `[read, search]` on **both** `_reviewer` and `_reviewer_web`; omit `web`, `execute`, `edit`, `agent`, and MCP tool globs (`web` + `COPILOT_ALLOW_ALL=1` creates an unrestricted local-read + auto-egress path, so Copilot audits workspace math/extracts and logs external URLs under `UNVERIFIED`).
- **Shadowing & OS isolation**: Prompt rules are not OS controls, and project-local `.agents/agents/` or `.github/agents/` silently overrides personal global profiles of the same name. Run `dot context --check` (and the preflight check in [headless-review](headless-review/GUIDE.md)) before reviewing untrusted repos, pair `--sandbox --settings '{"allowNonWorkspaceAccess":false}'` with `--disable-slash-commands`, and launch `fmind-review-factcheck` from `/var/tmp/<sandbox>` holding sanitized extracts with loopback `read_url` denies.
