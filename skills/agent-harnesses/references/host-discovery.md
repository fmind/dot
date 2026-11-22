# Host Discovery

Where managed hosts load the persona, global skills (`~/.agents/skills`), and workspace skills, plus their read-only check:

| Host        | Persona                              | Global skills                                  | Workspace skills                                        | Read-only listing                                      |
| ----------- | ------------------------------------ | ---------------------------------------------- | ------------------------------------------------------- | ------------------------------------------------------ |
| Antigravity | `~/.gemini/GEMINI.md` or `AGENTS.md` | `~/.gemini/config/skills` → `~/.agents/skills` | `.agents/skills`                                        | `/skills` in-session (`/skills reload` refreshes)      |
| Copilot     | `~/.copilot/copilot-instructions.md` | `~/.copilot/skills` or `~/.agents/skills`      | `.github/skills`, `.agents/skills`, or `.claude/skills` | `copilot skill list --json`; `instruction list --json` |

## Reading the output

- **Antigravity manifests & CLI overrides**: scans one level deep by default; `skills.json`, `rules.json`, `agents.json`, and `plugins.json` (`entries`/`inherits`/`exclude`) register nested or shared paths (`.gemini/config.json` `personal_customization_dir` supports per-user repo folders). CLI also loads `~/.gemini/antigravity-cli/skills/` and `~/.gemini/skills/`, which override workspace/personal skills and ignore manifest `exclude`.
- **`gh skill list`** (preview; `--agent`, `--scope`, `--json`) scans host directories on disk without proving runtime loading.
- **External/client repos**: preserve existing third-party host layouts (`AGENTS.md` + `.agents/skills` stay primary; cloud workers see only project or image-installed packages, not local `~` files).
- **Listings prove discovery only**: captured model inputs prove prompt inclusion, and instrumented test cases prove behavioral compliance.

## Same-name resolution

Observed precedence when skills or commands collide:

| Host        | Global vs project skill                       | Built-in command vs skill                          |
| ----------- | --------------------------------------------- | -------------------------------------------------- |
| Antigravity | Project overrides global                      | Print built-ins win; interactive untested          |
| Copilot     | Project > `--plugin-dir` > personal, silently | Built-in keeps `/name`; skill loses slash shortcut |

Keep skill names unique across global/project scopes and host built-ins; `dot context --check` flags duplicates between `~/.agents/skills` and `.agents/skills`.

## Native plugin catalogs

Check native host discovery before adding plugins, vet executable packages via [skill-security-review](../../code-security/references/skill-security-review/GUIDE.md), keep project vs user scope intact, and never dump a whole catalog into `~/.agents/skills`.
