# Repository Agent Host Setup

## Workflow

1. **Create the shared layer**:
   ```bash
   mkdir -p .agents/skills .agents/prompts
   ```
   Seed `AGENTS.md` from [AGENTS.md.template](../templates/AGENTS.md.template) when no stack template supplied one (suffixed `.template` so Claude Code and OpenCode do not auto-load it); `.agents/skills/<name>/SKILL.md` holds repo skills and gitignored `.agents/prompts/` holds handoffs. Antigravity, Copilot, Cursor, OpenCode, Pi, and other [AGENTS.md](https://agents.md) hosts (such as Codex) read both natively.
1. **Bridge Claude Code skills when needed**: Claude Code 2.1.277+ reads `AGENTS.md` when `CLAUDE.md` is absent (never add `CLAUDE.md`, which shadows `AGENTS.md` under default `instructionFiles`), but loads skills only from `.claude/skills`:
   ```bash
   mkdir -p .claude && ln -s ../.agents/skills .claude/skills
   ```
   If `.claude/` is gitignored, ignore its contents instead so the tracked symlink survives:
   ```gitignore
   !.claude/
   .claude/*
   !.claude/skills
   ```
1. **Add host files only on demand**:
   - **Antigravity**: honors `.gitignore`; check current docs for workspace/MCP paths.
   - **Claude Code**: `.mcp.json` (`claude mcp add --scope project`).
   - **Copilot**: `.github/copilot-instructions.md` for Copilot-only additions.
   - **Cursor**: `.cursor/rules`, `.cursor/cli.json` (permissions), `.cursor/mcp.json`.
   - **OpenCode**: `opencode.json`/`.jsonc` ([opencode](../../agent-harnesses/references/opencode/GUIDE.md)).
   - **Pi**: `.pi/settings.json` and `.pi/mcp.json`, loaded after trust ([pi](../../agent-harnesses/references/pi.md)).
1. **Verify**: launch each CLI at the repo root and check loaded instructions, skills, and MCP via [host discovery](host-discovery.md).

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

Add native host role files only when [cross-harness agents](cross-harness-agents.md) justifies them.
