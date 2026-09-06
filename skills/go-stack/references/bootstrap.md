# Go Project Bootstrap

## 2. Project Scaffolding Workflow

1. **Information**: define `Slug`, `Import Path` (e.g. `github.com/username/slug`), `Package` (a valid Go identifier, usually `Slug` without punctuation), and `Holder/Year`.
1. **Bootstrap**: `go mod init <import_path>` records the active toolchain version in `go.mod`.
1. **Tasks and hooks by project type**, saved as `mise.toml` and `lefthook.yml`:
   - Web: [mise.toml](references/mise.toml) + [lefthook.yml](references/lefthook.yml) (templ, Tailwind, vendor, and watch tasks).
   - CLI/agent: [mise-cli.toml](references/mise-cli.toml) + [lefthook-cli.yml](references/lefthook-cli.yml) (same vocabulary, no web tasks).
1. **Config files**:
   - `.golangci.yml` from [golangci.yml](references/golangci.yml) — replace `<import_path>` there and in the `format:go` task so `format` and `check` agree.
   - `dprint.json` per [dprint](../dprint/SKILL.md); `.air.toml` from [air.toml](references/air.toml) (web only).
   - `.env.example` from [env.example](references/env.example) (uncomment what the project type uses), `.gitignore` from [gitignore](references/gitignore).
   - `AGENTS.md` from [AGENTS.md](references/AGENTS.md) (drop the `(web)` lines for CLI/agent); `LICENSE` per [project-license](../project-license/SKILL.md).
1. **Toolchain**: `mise trust && mise install`, then `go get -tool golang.org/x/tools/cmd/goimports mvdan.cc/gofumpt golang.org/x/vuln/cmd/govulncheck` (web adds `github.com/a-h/templ/cmd/templ`).
1. **Sources**:
   - `cmd/<slug>/main.go` from [main.go](references/main.go) (web), [cli.go](references/cli.go) (CLI), or [agent.go](references/agent.go) (agent, plus `go get google.golang.org/adk/v2`).
   - `<package>.go` from [lib.go](references/lib.go) with [lib_test.go](references/lib_test.go); `config/config.go` from [config.go](references/config.go) (CLI/agent may drop `Port`).
   - Web: [server.go](references/server.go), [server_test.go](references/server_test.go), [middleware.go](references/middleware.go), [telemetry.go](references/telemetry.go).
   - Web templates and assets: [layout.templ](references/layout.templ), [home.templ](references/home.templ), [styles.css](references/styles.css), [app.js](references/app.js), [user-card.js](references/user-card.js).
   - Web vendoring: `scripts/vendor.go` from [vendor.go](references/vendor.go), run once by `install:vendor`.
1. **Validate**: `git init --initial-branch=main`, then `mise run install`, `mise run format`, `mise run check`, `mise run test`; before the first commit, `check:leaks` scans the working tree.
1. **Finish**: keep this stack's `AGENTS.md` when running [agent-project](../agent-project/SKILL.md), write `README.md` per [readme-md](../readme-md/SKILL.md), then report the verified result; if committing was requested, stage only the intended files and use [conventional-commit](../conventional-commit/SKILL.md).
