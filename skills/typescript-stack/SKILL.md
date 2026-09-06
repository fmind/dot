---
name: typescript-stack
description: "Configure the TypeScript toolbox and Angular-first web architecture with pnpm, Biome, tsc, tsx, Knip, and Vitest. Use for TypeScript tooling, websites, or an existing Node package."
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/typescript-stack
  created: "2026-09-02"
  updated: "2026-09-05"
---

# TypeScript Stack Standard

Keep the complete TypeScript toolbox while making Angular the default application architecture for websites. [angular](../angular/SKILL.md) owns application scaffolding; [firebase](../firebase/SKILL.md) adds backend services and [genkit](../genkit/SKILL.md) adds AI flows only when adopted.

## Defaults

- **Reproducible tools**: pnpm with a committed lockfile and project-local Biome, tsc, tsx, Knip, and Vitest where applicable; global mise tools are interactive conveniences.
- **Framework ownership**: Angular chooses its compatible TypeScript, builder, tests, angular-eslint, and Prettier split; do not overlay a Node package scaffold on an Angular app.
- **Quality**: strict types, validation at untrusted boundaries, focused behavior tests, unused-code checks, and one formatter per file. dprint owns markup/config outside the chosen code formatter's scope.
- **Architecture**: feature-oriented UI, explicit loading/error/empty states, accessible controls, and server-side authorization for privileged operations.

## Workflow

1. **Identify the product**: use [web architecture](references/web-architecture.md) to choose CSR/SSG/SSR and optional Firebase/Genkit; general CLIs and APIs default to Go or Python.
1. **Select the toolchain**: inspect project peer dependencies and lockfiles; use [tooling details](references/tooling.md) for compiler/runtime/formatter compatibility rather than imposing global versions.
1. **Choose a scaffold**: Angular owns applications. Read [node-project.md](references/node-project.md) only for an actual package, supported server function, Genkit flow, or MCP server.
1. **Validate**: run focused tests and the required mise gate using `pnpm exec`; update docs, then report local versus hosted proof. Commit or deploy only within existing authorization.

## References for the package/service profile

| Need                                               | Read                                                                                                                                                                                                                      |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Manifest and task wiring                           | [package.json.template](references/package.json.template), [mise.toml](references/mise.toml), [lefthook.yml](references/lefthook.yml)                                                                                     |
| Compiler, lint, dependency, and test configuration | [tsconfig.json](references/tsconfig.json), [tsconfig.build.json](references/tsconfig.build.json), [biome.json](references/biome.json), [knip.json](references/knip.json), [vitest.config.ts](references/vitest.config.ts) |
| Repository conventions                             | [AGENTS.md](references/AGENTS.md), [dprint.json](references/dprint.json), [gitignore](references/gitignore), [env.example](references/env.example)                                                                        |
| Public library surface and behavior                | [index.ts](references/index.ts), [lib.ts](references/lib.ts), [lib.test.ts](references/lib.test.ts)                                                                                                                       |
| Service entry, typed config, and logs              | [main.ts](references/main.ts), [config.ts](references/config.ts), [config.test.ts](references/config.test.ts), [logger.ts](references/logger.ts), [logger.test.ts](references/logger.test.ts)                             |

## Gotchas

- **tsx stays available**: use it for typed scripts or runtime features that native type stripping cannot handle; it is not Angular's builder.
- **Knip**: begin with framework auto-detection; add only evidenced exceptions for strings or task-only dependencies.
- **Client trust**: browser configuration is public; credentials, model keys, and privileged SDK operations remain behind independently authorized server handlers.
- **Runtime compatibility**: validate import extensions, compiler peers, and package-manager install policy against the actual project; version-specific recipes are reference material.

## Official Skills

Discover vendor bundles through the owning [Angular](../angular/SKILL.md), [Firebase](../firebase/SKILL.md), and [Genkit](../genkit/SKILL.md) skills; install only the reviewed capability the task needs.

## Documentation

- [TypeScript](https://www.typescriptlang.org/docs/) · [Node](https://nodejs.org/docs/latest/api/) · [pnpm](https://pnpm.io) · [Biome](https://biomejs.dev) · [Vitest](https://vitest.dev) · [Knip](https://knip.dev) · [Zod](https://zod.dev) · [pino](https://getpino.io)
- Companion skills: [angular](../angular/SKILL.md), [firebase](../firebase/SKILL.md), [genkit](../genkit/SKILL.md), [mcp-server](../mcp-server/SKILL.md), [playwright](../playwright/SKILL.md), [containerize](../containerize/SKILL.md), [github-actions](../github-actions/SKILL.md), [secure](../secure/SKILL.md).
