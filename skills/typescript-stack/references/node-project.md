# TypeScript Package and Service Profile

## 2. Project Scaffolding Workflow

Angular applications skip this section entirely and follow [angular](../angular/SKILL.md).

1. **Information**: define `Slug`, `Description`, and `Holder/Year`.
1. **Bootstrap**: `mkdir <slug> && cd <slug> && pnpm init`, then replace `package.json` with [package.json.template](references/package.json.template) — pin `packageManager` to the installed `pnpm --version` and drop `bin` unless the package ships an executable.
1. **Config files**: [tsconfig.json](references/tsconfig.json), [tsconfig.build.json](references/tsconfig.build.json), [biome.json](references/biome.json), [knip.json](references/knip.json), [vitest.config.ts](references/vitest.config.ts), [mise.toml](references/mise.toml), [lefthook.yml](references/lefthook.yml), [dprint.json](references/dprint.json), `.gitignore` from [gitignore](references/gitignore), `.env.example` from [env.example](references/env.example), `AGENTS.md` from [AGENTS.md](references/AGENTS.md), and `LICENSE` per [project-license](../project-license/SKILL.md).
1. **Sources**: every starter lands in `src/` — [index.ts](references/index.ts), [lib.ts](references/lib.ts), and [lib.test.ts](references/lib.test.ts) for a library; services and executables add [main.ts](references/main.ts), [config.ts](references/config.ts), [logger.ts](references/logger.ts), [config.test.ts](references/config.test.ts), and [logger.test.ts](references/logger.test.ts).
1. **Toolchain**: `mise trust && mise install`, then `pnpm install` (drop `zod`, `pino`, and `pino-pretty` from a library that needs neither); commit the `pnpm-workspace.yaml` pnpm writes.
1. **Validate**: `git init --initial-branch=main`, then `mise run install`, `mise run format`, `mise run check`, `mise run test`, `mise run build`; before the first commit, `check:leaks` scans the working tree.
1. **Finish**: write `README.md` per [readme-md](../readme-md/SKILL.md), then report the verified result; if committing was requested, stage only the intended files and use [conventional-commit](../conventional-commit/SKILL.md).

## 3. Project Profiles

- **Library**: `src/index.ts` is the whole public surface and the single `exports` entry; keep runtime dependencies at zero and run `check:pkg` before publishing.
- **Service or executable**: add `src/main.ts` (shebang when `package.json` declares `bin`), typed config, and a logger; run it with `node --watch src/main.ts` in development and `node dist/main.js` in production.
- **Genkit flow, MCP server, Firebase Function**: this scaffold plus the capability skill — [genkit](../genkit/SKILL.md), [mcp-server](../mcp-server/SKILL.md), or [firebase](../firebase/SKILL.md); Functions keep their own `package.json` on the runtime's Node version.
- **Angular website**: [angular](../angular/SKILL.md) owns the toolchain (Angular CLI, angular-eslint, Prettier, its own pinned TypeScript); only the conventions in §1 that Angular does not override apply.
