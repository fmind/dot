# Host Discovery

How each host finds the persona, global skills, and workspace skills, and the read-only command that lists what it loaded. Global paths follow the dotfiles layout where every host path links back to `~/.agents/AGENTS.md` and `~/.agents/skills`.

| Host        | Persona                                              | Global skills                                                       | Workspace skills                                        | Read-only listing                           |
| ----------- | ---------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------- | ------------------------------------------- |
| Antigravity | `~/.gemini/GEMINI.md`                                | `~/.gemini/config/skills` (link to `~/.agents/skills`)              | `.agents/skills`                                        | `/skills` inside the session (unverified)   |
| Claude Code | `~/.claude/CLAUDE.md`                                | `~/.claude/skills` (link to `~/.agents/skills`)                     | `.claude/skills` (link to `../.agents/skills`)          | `/skills` inside the session                |
| Codex       | `~/.codex/AGENTS.md`                                 | `~/.agents/skills`                                                  | `.agents/skills`                                        | `codex debug prompt-input`                  |
| Copilot     | `~/.copilot/copilot-instructions.md`                 | `~/.copilot/skills` or `~/.agents/skills`                           | `.github/skills`, `.agents/skills`, or `.claude/skills` | `copilot skill list`                        |
| Grok        | `~/.grok/AGENTS.md`                                  | `~/.grok/skills` (link to `~/.agents/skills`)                       | `.agents/skills`                                        | `grok inspect`                              |

## Reading the output

- `codex debug prompt-input` renders the model-visible prompt as JSON: check every expected name and front-loaded routing cue, record any description truncation, and keep the CLI version and model because the metadata budget depends on them.
- `copilot skill list` groups skills by source (project, personal, plugin); `--json` gives machine-readable output.
- `grok inspect` lists project instructions, permissions, and every skill with its scope (`project` or `user`); `--json` is available.
- Claude Code and Antigravity expose `/skills` in the interactive session only; explicit invocation (`/<skill-name>`) is the fallback proof in Claude.
- A listed skill proves inclusion in the prompt, not instruction following; validate behavior against explicit acceptance cases in a disposable, instrumented run.

## Native plugin catalogs

Use the installed host's native discovery before adding a plugin: `anthropics/skills` is Anthropic's skill bundle and `openai/plugins` is the Codex plugin catalog. Read the relevant package only when a task needs it, review executable integrations per [skill-security-review](../../skill-security-review/SKILL.md), and preserve project versus user scope. Do not install an entire catalog into the shared personal skills directory.
