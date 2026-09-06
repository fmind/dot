# Repository Agent Host Setup

## Workflow

1. **Create the shared layer**:
   ```bash
   mkdir -p .agents/skills .agents/prompts
   ```
   Start `AGENTS.md` from the [project template](templates/AGENTS.md); project skills live in `.agents/skills/<name>/SKILL.md` and handover prompts in `.agents/prompts/` (gitignored).
1. **Bridge Claude Code**: Claude reads `CLAUDE.md` and `.claude/skills`, not `AGENTS.md` and `.agents/skills`. After checking that neither path already exists unmanaged:
   ```bash
   ln -s AGENTS.md CLAUDE.md                          # or a CLAUDE.md containing only `@AGENTS.md`
   mkdir -p .claude && ln -s ../.agents/skills .claude/skills
   ```
   When `.claude/` or `CLAUDE.md` is gitignored (globally or in the repository), un-ignore both tracked entries so every clone gets them; a directory rule cannot be re-included, so ignore the contents instead:
   ```gitignore
   .claude/*
   !.claude/skills
   !CLAUDE.md
   ```
1. **Add host files only when needed**:
   - **Antigravity**: reads `AGENTS.md` and `.agents/skills`; workspace settings and MCP file paths follow its current docs and it respects `.gitignore`.
   - **Claude Code**: `.mcp.json` for project MCP servers (`claude mcp add --scope project`).
   - **Codex**: reads `AGENTS.md` and `.agents/skills`; `.codex/config.toml` holds trusted project overrides and MCP.
   - **Copilot**: reads `AGENTS.md` and `.agents/skills`; `.github/copilot-instructions.md` only for extra repository-wide Copilot instructions.
   - **Grok**: reads `AGENTS.md` and `.agents/skills`; project MCP lives in `./.grok/config.toml` via `grok mcp add --scope project`.
   - **OpenCode**: reads `AGENTS.md` and `.agents/skills`; `opencode.json` holds project settings and MCP.
1. **Keep secrets and state out of git**: ignore local credentials, generated agent state, and secret-bearing overrides; commit only portable configuration.
1. **Verify each installed CLI**: start it from the repository root and confirm instructions, skills, and configured MCP servers load, using the listing commands in [host discovery](references/host-discovery.md).

## Layout

```text
<repo>/
├── AGENTS.md                          # shared instructions for all six hosts
├── CLAUDE.md -> AGENTS.md             # Claude bridge (or a file containing @AGENTS.md)
├── .agents/
│   ├── prompts/                       # handover prompts, gitignored
│   └── skills/<name>/SKILL.md         # project skills
├── .claude/skills -> ../.agents/skills
├── .codex/config.toml                 # optional: Codex overrides and MCP
├── .github/copilot-instructions.md    # optional: extra Copilot instructions
├── .grok/config.toml                  # optional: Grok project MCP
├── .mcp.json                          # optional: Claude project MCP
└── opencode.json                      # optional: OpenCode settings and MCP
```

## Custom agents

Custom-agent definitions are not portable; keep them in each host's native location instead of a shared `.agents/agents`, give parallel agents bounded tasks with non-overlapping file ownership, and let the parent integrate and validate.

| Host        | Project location                                        |
| ----------- | ------------------------------------------------------- |
| Antigravity | `.agents/agents/<name>/agent.md`                        |
| Claude Code | `.claude/agents/<name>.md`                              |
| Codex       | `.codex/agents/<name>.toml`                             |
| Copilot     | `.github/agents/<name>.agent.md`                        |
| Grok        | `grok --agent <definition-file>` (no project directory) |
| OpenCode    | `.opencode/agents/<name>.md`                            |
