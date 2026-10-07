# Host Discovery

How each host finds the persona, global skills, and workspace skills, and the read-only command that lists what it loaded. Global paths follow the dotfiles layout where every host path links back to `~/.agents/AGENTS.md` and `~/.agents/skills`.

| Host        | Persona                                          | Global skills                                          | Workspace skills                                        | Read-only listing                                                          |
| ----------- | ------------------------------------------------ | ------------------------------------------------------ | ------------------------------------------------------- | -------------------------------------------------------------------------- |
| Antigravity | `~/.gemini/GEMINI.md`                            | `~/.gemini/config/skills` (link to `~/.agents/skills`) | `.agents/skills`                                        | `/skills` inside the session                                               |
| Claude Code | `~/.claude/CLAUDE.md`; project `AGENTS.md`       | `~/.claude/skills` (link to `~/.agents/skills`)        | `.claude/skills` (link to `../.agents/skills`)          | `/skills` inside the session                                               |
| Codex       | `~/.codex/AGENTS.md`                             | `~/.agents/skills`                                     | `.agents/skills`                                        | `codex debug prompt-input`                                                 |
| Copilot     | `~/.copilot/copilot-instructions.md`             | `~/.copilot/skills` or `~/.agents/skills`              | `.github/skills`, `.agents/skills`, or `.claude/skills` | `copilot skill list`                                                       |
| Cursor      | Project `AGENTS.md` and Cursor rules             | `~/.agents/skills` or `~/.cursor/skills`               | `.agents/skills` or `.cursor/skills`                    | Skills in Customize; no standalone skill-list command in the inspected CLI |
| Grok        | `~/.grok/AGENTS.md`                              | `~/.grok/skills` (link to `~/.agents/skills`)          | `.agents/skills`                                        | `grok inspect`                                                             |
| OpenCode    | `~/.config/opencode/AGENTS.md` (managed symlink) | `~/.agents/skills`                                     | `.agents/skills` or `.opencode/skills`                  | `opencode debug skill`                                                     |

## Reading the output

- `codex debug prompt-input` renders the model-visible prompt as JSON: check every expected name and front-loaded routing cue, record any description truncation, and keep the CLI version and model because the metadata budget depends on them.
- `copilot skill list` groups skills by source (project, personal, plugin); `--json` gives machine-readable output.
- `grok inspect` lists project instructions, permissions, and every skill with its scope (`project` or `user`); `--json` is available.
- Claude Code and Antigravity expose `/skills` in the interactive session only; explicit invocation (`/<skill-name>`) is the fallback proof in Claude.
- `opencode debug skill` can include skill bodies; inspect needed names locally and keep private instruction content out of reports.
- `gh skill list` (preview) scans every supported host's project and user directories in one pass; `--agent`, `--scope`, and `--json` narrow it. It proves files are present, not that a host loaded them.
- **Listings prove only discovery**: A listing proves discovery by that interface; only a captured model input proves prompt inclusion, and neither proves instruction following. Validate behavior against explicit acceptance cases in a disposable, instrumented run.
- Cursor also discovers compatibility directories documented in [its skills guide](https://cursor.com/docs/skills). User-level packages remain local unless explicitly distributed to a remote execution environment; use project packages or worker-image installation for Cloud Agents and self-hosted workers.

## Same-name resolution

Hosts disagree when two skills, or a skill and a command, share a name (checked 2026-10-04):

| Host        | Global vs project skill                       | Built-in command vs skill                                                                     |
| ----------- | --------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Antigravity | Project overrides global                      | Print-mode built-ins win; interactive built-ins untested                                      |
| Claude Code | Personal (`~/.claude/skills`) beats project   | Skill replaces the built-in (not its aliases)                                                 |
| Codex       | Both copies listed; the model picks           | No clash: skills use `$name`, not `/name`                                                     |
| Copilot     | Project > `--plugin-dir` > personal, silently | Built-in keeps `/name`; the skill loses its slash command                                     |
| Grok        | Local > repo > user                           | Built-in keeps `/name`; skill reachable as `/<scope>:name` (e.g. `/local:name`, `/user:name`) |
| OpenCode    | Nondeterministic; logs `duplicate skill name` | Built-in, custom, and MCP commands keep the name                                              |

A symlinked `.claude/skills` -> `.agents/skills` layout exposes the same files twice; OpenCode then picks one path per name at random and logs `duplicate skill name`, so fish exports `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1` to keep it on `.agents/skills`. Otherwise keep skill names unique across global and project scopes and distinct from host built-in commands; `dot agent context --check` fails on duplicates between `~/.agents/skills` and the project's `.agents/skills`; other host directories are not checked.

## Native plugin catalogs

Use the installed host's native discovery before adding a plugin: `anthropics/skills` is Anthropic's skill bundle and `openai/plugins` is the Codex plugin catalog. Read the relevant package only when a task needs it, review executable integrations per [skill-security-review](../../skill-security-review/SKILL.md), and preserve project versus user scope. Do not install an entire catalog into the shared personal skills directory.
