# Host Discovery

How each host finds the persona, global skills, and workspace skills, and the read-only command that lists what it loaded. Global paths follow the dotfiles layout where every host path links back to `~/.agents/AGENTS.md` and `~/.agents/skills`.

| Host        | Persona                                          | Global skills                                          | Workspace skills                                        | Read-only listing                                                          |
| ----------- | ------------------------------------------------ | ------------------------------------------------------ | ------------------------------------------------------- | -------------------------------------------------------------------------- |
| Antigravity | `~/.gemini/GEMINI.md`                            | `~/.gemini/config/skills` (link to `~/.agents/skills`) | `.agents/skills`                                        | `/skills` inside the session                                               |
| Claude Code | `~/.claude/CLAUDE.md`; project `AGENTS.md`       | `~/.claude/skills` (link to `~/.agents/skills`)        | `.claude/skills` (link to `../.agents/skills`)          | `/skills` inside the session                                               |
| Copilot     | `~/.copilot/copilot-instructions.md`             | `~/.copilot/skills` or `~/.agents/skills`              | `.github/skills`, `.agents/skills`, or `.claude/skills` | `copilot skill list`; `copilot instruction list`                           |
| Cursor      | Project `AGENTS.md` and Cursor rules             | `~/.agents/skills` or `~/.cursor/skills`               | `.agents/skills` or `.cursor/skills`                    | Skills in Customize; no standalone skill-list command in the inspected CLI |
| OpenCode    | `~/.config/opencode/AGENTS.md` (managed symlink) | `~/.agents/skills`                                     | `.agents/skills` or `.opencode/skills`                  | None in 2.x; a bounded run that loads the skill by ID                      |

## Reading the output

- `copilot skill list` groups skills by source (project, personal, plugin), and `copilot instruction list` shows the instruction files a session would load; both take `--json`.
- Claude Code and Antigravity expose `/skills` in the interactive session only; explicit invocation (`/<skill-name>`) is the fallback proof in Claude.
- OpenCode 2.x removed `opencode debug skill`; its skill ID is the directory name, not the frontmatter `name`.
- `gh skill list` (preview) scans every supported host's project and user directories in one pass; `--agent`, `--scope`, and `--json` narrow it. It proves files are present, not that a host loaded them.
- **Listings prove only discovery**: A listing proves discovery by that interface; only a captured model input proves prompt inclusion, and neither proves instruction following. Validate behavior against explicit acceptance cases in a disposable, instrumented run.
- Cursor also discovers compatibility directories documented in [its skills guide](https://cursor.com/docs/skills). User-level packages remain local unless explicitly distributed to a remote execution environment; use project packages or worker-image installation for Cloud Agents and self-hosted workers.

## Same-name resolution

Hosts disagree when two skills, or a skill and a command, share a name (checked 2026-10-04):

| Host        | Global vs project skill                       | Built-in command vs skill                                 |
| ----------- | --------------------------------------------- | --------------------------------------------------------- |
| Antigravity | Project overrides global                      | Print-mode built-ins win; interactive built-ins untested  |
| Claude Code | Personal (`~/.claude/skills`) beats project   | Skill replaces the built-in (not its aliases)             |
| Copilot     | Project > `--plugin-dir` > personal, silently | Built-in keeps `/name`; the skill loses its slash command |
| OpenCode    | Later source wins: project over global        | Built-in, custom, and MCP commands keep the name          |

A symlinked `.claude/skills` -> `.agents/skills` layout exposes the same files twice; OpenCode 2.x registers `.claude/skills`, then `.agents/skills`, `~/.config/opencode/skills`, and `.opencode/skills`, and the later source wins, so fish exports `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1` to scan the catalog once. Otherwise keep skill names unique across global and project scopes and distinct from host built-in commands; `dot agent context --check` fails on duplicates between `~/.agents/skills` and the project's `.agents/skills`; other host directories are not checked.

## Native plugin catalogs

Use the installed host's native discovery before adding a plugin: for example, `anthropics/skills` is Anthropic's skill bundle. Read the relevant package only when a task needs it, review executable integrations per [skill-security-review](../../code-security/references/skill-security-review/GUIDE.md), and preserve project versus user scope. Do not install an entire catalog into the shared personal skills directory.
