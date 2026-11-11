# Host Discovery

Where each host loads the persona, global skills (`~/.agents/skills`), and workspace skills, plus its read-only check:

| Host        | Persona                                    | Global skills                                  | Workspace skills                                        | Read-only listing                                      |
| ----------- | ------------------------------------------ | ---------------------------------------------- | ------------------------------------------------------- | ------------------------------------------------------ |
| Antigravity | `~/.gemini/GEMINI.md`                      | `~/.gemini/config/skills` → `~/.agents/skills` | `.agents/skills`                                        | `/skills` in-session                                   |
| Claude Code | `~/.claude/CLAUDE.md`; project `AGENTS.md` | `~/.claude/skills` → `~/.agents/skills`        | `.claude/skills` → `../.agents/skills`                  | `/skills` in-session (`/<skill-name>` fallback)        |
| Copilot     | `~/.copilot/copilot-instructions.md`       | `~/.copilot/skills` or `~/.agents/skills`      | `.github/skills`, `.agents/skills`, or `.claude/skills` | `copilot skill list --json`; `instruction list --json` |
| Cursor      | Project `AGENTS.md` and Cursor rules       | `~/.agents/skills` or `~/.cursor/skills`       | `.agents/skills` or `.cursor/skills`                    | Customize UI (no CLI skill-list command)               |
| OpenCode    | `~/.config/opencode/AGENTS.md` (symlink)   | `~/.agents/skills`                             | `.agents/skills` or `.opencode/skills`                  | None in 2.x; bounded run loading directory ID          |
| Pi          | `~/.pi/agent/AGENTS.md` (symlink)          | `~/.agents/skills` or `~/.pi/agent/skills`     | `.agents/skills` or `.pi/skills` (after project trust)  | Interactive startup header                             |

## Reading the output

- **OpenCode 2.x** dropped `opencode debug skill`; skill IDs match directory names, not frontmatter `name`.
- **Pi** skips workspace skills in untrusted checkouts (headless runs see global skills only unless trusted via `dot trust`).
- **`gh skill list`** (preview; `--agent`, `--scope`, `--json`) scans host directories on disk without proving runtime loading.
- **Cursor** also checks compatibility paths in [its skills guide](https://cursor.com/docs/skills); cloud/remote workers see only project or image-installed packages, not local `~` files.
- **Listings prove discovery only**: captured model inputs prove prompt inclusion, and only instrumented test cases prove behavioral compliance.

## Same-name resolution

Observed precedence when skills or commands collide (checked 2026-10-04):

| Host        | Global vs project skill                       | Built-in command vs skill                          |
| ----------- | --------------------------------------------- | -------------------------------------------------- |
| Antigravity | Project overrides global                      | Print built-ins win; interactive untested          |
| Claude Code | Personal (`~/.claude/skills`) beats project   | Skill overrides built-in (not aliases)             |
| Copilot     | Project > `--plugin-dir` > personal, silently | Built-in keeps `/name`; skill loses slash shortcut |
| OpenCode    | Later wins: project over global               | Built-in, custom, and MCP commands win             |
| Pi          | First wins: project, then global              | Skills use `/skill:<name>` (no collision)          |

Because `.claude/skills` → `.agents/skills` exposes skills twice in OpenCode 2.x (`.claude/skills`, `.agents/skills`, `~/.config/opencode/skills`, `.opencode/skills`), fish sets `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1`. Keep skill names unique across global/project scopes and host built-ins; `dot agent context --check` flags duplicates between `~/.agents/skills` and `.agents/skills`.

## Native plugin catalogs

Check native host discovery (such as `anthropics/skills`) before adding plugins, vet executable packages via [skill-security-review](../../code-security/references/skill-security-review/GUIDE.md), keep project vs user scope intact, and never dump a whole catalog into `~/.agents/skills`.
