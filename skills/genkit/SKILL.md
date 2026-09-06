---
name: genkit
description: Build Genkit AI flows, tools, prompts, and RAG in TypeScript, Go, or Python with the Genkit CLI and dev UI. Use when a project adopts Genkit instead of ADK.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/genkit
  created: "2026-09-02"
  updated: "2026-09-05"
---

# Genkit

Genkit is Firebase's framework for AI features inside an application: flows, tools, Dotprompt files, RAG, and a developer UI with traces. Agents that need multi-agent trees, A2A, or Agent Runtime stay on [google-adk](../google-adk/SKILL.md); Genkit fits TypeScript apps that already run on Firebase or Cloud Run.

## 1. Setup

- **CLI**: TypeScript uses `pnpm add -D genkit-cli` and commits `pnpm-lock.yaml`; Go/Python can use project-local `mise use npm:genkit-cli@latest` and commit `mise.lock`.
- **Packages**: TypeScript `genkit` and `@genkit-ai/google-genai` (`googleAI()` plugin); Go `github.com/firebase/genkit/go/{genkit,ai,plugins/googlegenai}`; Python `genkit`.
- **Docs**: `pnpm exec genkit docs:search "<topic>" <language>` searches the current documentation.

## 2. Development Loop

```bash
pnpm exec genkit start -- pnpm exec tsx --watch src/index.ts   # TypeScript: dev UI with traces
mise exec -- genkit start -- go run .                         # Go with the project mise tool
pnpm exec genkit flow:run <flowName> '{"input": "..."}' -- pnpm exec tsx src/index.ts
pnpm exec genkit trace:list
pnpm exec genkit trace:get <id> --format json
```

- Run flows through `genkit start` or `flow:run`; a plain `node`/`go run` skips trace capture and debugs blind.
- `genkit start` does not exit; automation uses `flow:run`.
- Wrap the loop in the canonical tasks: `watch` starts the dev UI, `test` calls `flow:run` against fixtures, per [mise](../mise/SKILL.md).

## 3. Rules

- **Typed flows**: Zod (TypeScript) or struct (Go) schemas on every flow input and output; the schema is the contract the UI and tests use.
- **Prompts as files**: `.prompt` (Dotprompt) files beside the code, versioned and reviewed like code per [prompt-design](../prompt-design/SKILL.md).
- **Model pins**: name the model generation explicitly; keep the plugin config in the typed project config, keys in env or Secret Manager.
- **Deploy**: Cloud Functions for Firebase (`@genkit-ai/firebase`) per [firebase](../firebase/SKILL.md), or a container per [cloud-run](../cloud-run/SKILL.md).
- **Evaluate**: `genkit eval:flow` datasets before shipping a prompt change; compare against a baseline per [agent-evaluation](../agent-evaluation/SKILL.md).

## Official Skills

Upstream: `genkit-ai/skills`. List the current release, then install what the task needs at project scope after reviewing the snapshot (see [native skill tooling](https://skills.sh/docs/cli)):

```bash
skills add genkit-ai/skills --list
skills add genkit-ai/skills --skill <name> -y
```

## Documentation

- [Genkit](https://genkit.dev) · [genkit-ai/skills](https://github.com/genkit-ai/skills)
- Companion skills: [typescript-stack](../typescript-stack/SKILL.md), [firebase](../firebase/SKILL.md), [google-adk](../google-adk/SKILL.md).
