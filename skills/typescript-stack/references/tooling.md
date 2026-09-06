# TypeScript Tooling Details

- **Runtime and language**: Node LTS (24) with ESM only, TypeScript 7 (the Go-native compiler); `strict` is on by default and `erasableSyntaxOnly` keeps sources runnable by `node src/main.ts` with no build step.
- **Dependencies**: `pnpm` exclusively — `pnpm add`, `pnpm exec`, `pnpm install --frozen-lockfile`; commit `pnpm-lock.yaml`.
- **Tasks and hooks**: [mise.toml](references/mise.toml) exposes the canonical vocabulary per [mise](../mise/SKILL.md); [lefthook.yml](references/lefthook.yml) wires pre-commit and pre-push per [lefthook](../lefthook/SKILL.md).
- **Formatting and linting**: Biome ([biome.json](references/biome.json)) owns TypeScript, JavaScript, JSON, and CSS plus import sorting; dprint ([dprint.json](references/dprint.json)) keeps Markdown, TOML, and YAML per [dprint](../dprint/SKILL.md).
- **Types**: `tsc --noEmit` is the type gate over sources, tests, and configs ([tsconfig.json](references/tsconfig.json)); [tsconfig.build.json](references/tsconfig.build.json) is the only config that emits.
- **Testing**: Vitest with the v8 provider and an 85% coverage gate ([vitest.config.ts](references/vitest.config.ts)); tests are `*.test.ts` files beside the code they cover.
- **Dependency hygiene**: Knip is `check:deps` and starts from auto-detection; [knip.json](references/knip.json) only lists what it provably cannot see.
- **Security**: `pnpm audit --audit-level high` is `check:vuln` and `gitleaks` is `check:leaks`; SAST is opt-in per [opengrep](../opengrep/SKILL.md).
- **Validation and config**: Zod v4 parses every untrusted boundary; `loadConfig()` reads the environment once at startup and fails fast ([config.ts](references/config.ts)).
- **Logging**: `pino` — `pino-pretty` locally, Cloud Logging JSON (`severity`, `message`) in production ([logger.ts](references/logger.ts)) per [observability](../observability/SKILL.md).
- **Publishing**: `publint` as `check:pkg` for anything published to npm; `pnpm dlx @arethetypeswrong/cli --pack .` before the first release.

## Compatibility and gotchas

- **TypeScript 7 changed defaults**: `strict` is on, `module` defaults to `esnext`, and `types` defaults to `[]` — list `["node"]` explicitly or every ambient `@types` package disappears. The programmatic API only stabilizes in 7.1, so tools embedding the compiler may still need TypeScript 6.
- **Angular pins its own TypeScript**: Angular 22 peers `typescript >=6.0 <6.1`, so an Angular repository is not on TypeScript 7; let `ng update` move it and never share one `tsconfig` across both.
- **pnpm 11 guards the supply chain**: `minimumReleaseAge` defaults to one day, so a just-published version resolves only after `pnpm-workspace.yaml` lists it under `minimumReleaseAgeExclude`, and dependency build scripts are blocked until `pnpm approve-builds` records them under `allowBuilds`. pnpm writes that file even in a single-package repository — commit it.
- **Global tools are not project pins**: the global `tsc`, `biome`, and `knip` from mise are conveniences; repository tasks always use `pnpm exec` so hooks and CI run the lockfile's versions.
- **One formatter per file**: Biome owns `**/*.json`, so `dprint.json` must exclude it; Angular projects replace Biome with the Angular skill's Prettier split because Biome does not format Angular templates.
- **Measure type-aware linting**: one prior repository measurement found a large cost; this is not a universal ratio. enabling the `types` domain (`noFloatingPromises`, `noMisusedPromises`) starts the project scanner — measured at ~14s against ~0.6s for the `project` and `test` domains and ~0.8s for a full `tsc --noEmit`. Leave it off unless unhandled rejections are a real risk, and enable the rules explicitly: they ship in `nursery` at `info` severity, so the domain alone never fails `check`.
- **Node runs TypeScript, not all of it**: type stripping rejects `enum`, `namespace`, and parameter properties — `erasableSyntaxOnly` catches them at type-check time. Reach for `tsx` only when a project needs `tsconfig` path aliases, decorators, or CJS interop.
- **Import the `.ts` extension**: `allowImportingTsExtensions` plus `rewriteRelativeImportExtensions` lets the same source run under `node` and emit `./x.js`; writing `./x.js` in source breaks running from `src/`.
- **Knip cannot see mise tasks**: a tool invoked only by `mise run` (Biome, publint) or referenced by string (`pino-pretty` as a pino transport) is reported unused — add it to `ignoreDependencies`, never a `package.json` script that duplicates the task.
- **The browser is untrusted**: Firebase web configuration ships to clients, but service-account credentials, model keys, and privileged operations stay server-side; Admin SDK calls bypass Security Rules, so server handlers authorize every operation themselves, and App Check is defense in depth — monitor legitimate traffic before enforcing, because enforcement rejects unverified clients.
