# Repository Agent Host Setup

## Workflow

1. **Create the shared layer**:
   ```bash
   mkdir -p .agents/skills .agents/prompts
   ```
   Start `AGENTS.md` from the [project template](../templates/AGENTS.md.template) (named `.template` because agy loads any `AGENTS.md` beside a file it reads); project skills live in `.agents/skills/<name>/SKILL.md` and handover prompts in `.agents/prompts/` (gitignored). Antigravity, Copilot, Cursor, and OpenCode read `AGENTS.md` and `.agents/skills` natively, as do other hosts that follow the [AGENTS.md standard](https://agents.md) (for example Codex); check such a host's docs for its own files.
1. **Bridge Claude Code skills only when the repository is also used with Claude Code**: Claude Code 2.1.277+ loads project `AGENTS.md` when no `CLAUDE.md` exists, so add no `CLAUDE.md`; a present one replaces `AGENTS.md` under the default `instructionFiles` mode. Its skills still load only from `.claude/skills`. After checking that the path does not already exist unmanaged:
   ```bash
   mkdir -p .claude && ln -s ../.agents/skills .claude/skills
   ```
   When `.claude/` is gitignored (globally or in the repository), un-ignore the tracked link so every clone gets it; a directory rule cannot be re-included, so ignore the contents instead:
   ```gitignore
   !.claude/
   .claude/*
   !.claude/skills
   ```
1. **Add host files only when needed**:
   - **Antigravity**: workspace settings and MCP file paths follow its current docs and it respects `.gitignore`.
   - **Claude Code**: `.mcp.json` for project MCP servers (`claude mcp add --scope project`).
   - **Copilot**: `.github/copilot-instructions.md` only for extra repository-wide Copilot instructions.
   - **Cursor**: `.cursor/rules` only for Cursor-specific rules. `.cursor/cli.json` owns project permissions and `.cursor/mcp.json` owns project MCP.
   - **OpenCode**: `opencode.json` or `.jsonc` for project configuration and MCP. See [opencode](../../agent-harnesses/references/opencode/GUIDE.md) for session operation.
1. **Verify each installed CLI**: start it from the repository root and confirm instructions, skills, and configured MCP servers load, using the listing commands in [host discovery](host-discovery.md).

## Layout

```text
<repo>/
├── AGENTS.md                          # shared project instructions
├── .agents/
│   ├── prompts/                       # handover prompts, gitignored
│   └── skills/<name>/SKILL.md         # project skills
├── .claude/skills -> ../.agents/skills # only when Claude Code is used
├── .github/copilot-instructions.md    # optional: extra Copilot instructions
├── .mcp.json                          # optional: Claude project MCP
```

## Custom agents

Native agent definitions differ by host. Add a role only when [cross-harness agents](cross-harness-agents.md) shows it pays off; that guide lists each host's project and personal locations.
