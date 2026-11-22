# Repository Agent Host Setup

## Workflow

1. **Create the shared layer**:
   ```bash
   mkdir -p .agents/skills .agents/prompts
   ```
   Seed `AGENTS.md` from [AGENTS.md.template](../templates/AGENTS.md.template) when no stack template supplied one (suffixed `.template` so hosts do not auto-load it); `.agents/skills/<name>/SKILL.md` holds repo skills and gitignored `.agents/prompts/` holds handoffs. Antigravity, Copilot, Cursor, and other [AGENTS.md](https://agents.md) hosts read both natively.
1. **Keep unused host state ignored**: keep `.claude/` and `.gemini/` in `.gitignore` without creating `.claude/skills` symlinks or `CLAUDE.md` files; Antigravity, Copilot, and other [AGENTS.md](https://agents.md) hosts read `AGENTS.md` and `.agents/skills/` natively.
1. **Add host files only on demand**:
   - **Antigravity**: honors `.gitignore`; check current docs for workspace/MCP paths.
   - **Copilot**: `.github/copilot-instructions.md` for Copilot-only additions.
   - **Client/external hosts** (when collaborating on third-party repos): preserve the host files the repository already maintains.
1. **Verify**: launch each CLI at the repo root and check loaded instructions, skills, and MCP via [host discovery](host-discovery.md); add native host role files only when [cross-harness agents](cross-harness-agents.md) justifies them.
