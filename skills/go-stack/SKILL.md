---
name: go-stack
description: Build Go projects, libraries, CLIs, TUIs, GOTH web apps, or ADK agents with the standard package layout and pinned tooling. Use for any Go work.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/go-stack
  created: "2026-06-23"
  updated: "2026-09-05"
---

# Go Stack Standard

Use Go for libraries, CLIs, TUIs, GOTH applications, and the API side of ADK agents. [google-adk](../google-adk/SKILL.md) owns agent orchestration; [hugo](../hugo/SKILL.md) owns content sites.

## Defaults

- **Toolchain**: latest stable Go, project-local `go tool` directives for generators/formatters/security tools, and mise pins for standalone CLIs.
- **Quality**: goimports and gofumpt; golangci-lint with zero warnings; standard `testing` through gotestsum. Add richer assertions only when useful.
- **Design**: domain logic in the root package, command wiring in `cmd/<slug>`; typed configuration parsed and validated once; explicit errors and timeouts.
- **Runtime**: `log/slog`, readable locally and JSON in production; OpenTelemetry only where the service or agent needs it. Keep SQL explicit and schema ownership in [atlas](../atlas/SKILL.md).
- **Profiles**: urfave/cli for CLIs, Charm for TUIs, ServeMux/Templ/HTMX/Alpine/Tailwind for GOTH, and the verified installed ADK API for agents.

## Workflow

1. **Inspect before scaffolding**: preserve the existing architecture, supported Go version, and dirty work; select the matching [profile](references/profiles.md).
1. **Bootstrap when needed**: follow [bootstrap.md](references/bootstrap.md), materializing only that profile's files from the map below.
1. **Implement and verify**: use `mise run` tasks from [mise](../mise/SKILL.md); run focused behavior checks, then the required complete gate. Keep generators and their committed output consistent.
1. **Finish**: update [README](../readme-md/SKILL.md) and [agent instructions](../agents-md/SKILL.md), report evidence, and commit only when requested with scoped staging.

## References by task

| Need                                     | Read                                                                                                                                                                                                                       |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CLI/agent tasks and hooks                | [mise-cli.toml](references/mise-cli.toml), [lefthook-cli.yml](references/lefthook-cli.yml)                                                                                                                                 |
| Web tasks, hooks, and reload             | [mise.toml](references/mise.toml), [lefthook.yml](references/lefthook.yml), [air.toml](references/air.toml), [web-gotchas.md](references/web-gotchas.md)                                                                   |
| Shared project configuration             | [golangci.yml](references/golangci.yml), [AGENTS.md](references/AGENTS.md), [env.example](references/env.example), [gitignore](references/gitignore), [layouts.md](references/layouts.md)                                  |
| Library, configuration, and entry points | [lib.go](references/lib.go), [lib_test.go](references/lib_test.go), [config.go](references/config.go), [cli.go](references/cli.go), [agent.go](references/agent.go), [main.go](references/main.go)                         |
| Web server and instrumentation           | [server.go](references/server.go), [server_test.go](references/server_test.go), [middleware.go](references/middleware.go), [telemetry.go](references/telemetry.go)                                                         |
| Templates and embedded assets            | [layout.templ](references/layout.templ), [home.templ](references/home.templ), [styles.css](references/styles.css), [app.js](references/app.js), [user-card.js](references/user-card.js), [vendor.go](references/vendor.go) |

## Gotchas

- **Installed APIs**: inspect the resolved module source before using a dependency; templates are defaults that must match the project's version.
- **Wire compatibility**: `omitzero` and `omitempty` omit different values; choose against the API contract rather than mechanically replacing tags.
- **Assets**: authored web sources belong in `assets/`; generated/vendored output belongs in embedded `static/`. Read the web gotchas before changing generation or load order.
- **Images**: `build:image` defaults to local output; registry writes require the explicitly authorized `--push=true` path in [containerize](../containerize/SKILL.md).

## Documentation

- [Go](https://go.dev/doc/) · [Templ](https://templ.guide) · [HTMX](https://htmx.org) · [Alpine.js](https://alpinejs.dev) · [Tailwind CSS](https://tailwindcss.com) · [esbuild](https://esbuild.github.io/) · [ADK for Go](https://google.github.io/adk-docs/get-started/go/)
- Companion skills: [google-adk](../google-adk/SKILL.md) (agent workflow), [cli-contracts](../cli-contracts/SKILL.md), [containerize](../containerize/SKILL.md), [github-actions](../github-actions/SKILL.md), [secure](../secure/SKILL.md), [update-docs](../update-docs/SKILL.md).
