# Go Profiles and Idioms

## 3. Database & Persistence

- **SQL first**: raw SQL with `sqlc`-generated types over `jackc/pgx/v5` (`pgxpool` with explicit bounds and timeouts); schema linting and migrations per [atlas](../atlas/SKILL.md), or `goose` for versioned SQL migrations.

## 4. Web Stack (GOTH)

- **Router**: `http.ServeMux` path-value routing; `go-chi/chi/v5` when middleware stacks grow.
- **Type-safe REST**: Huma (`github.com/danielgtaylor/huma/v2`) for OpenAPI 3.1 and JSON Schema validation.
- **UI components**: Templ co-locates markup, styling, and state; an Alpine component moves to `assets/js/components/<name>.js` once it grows methods or is reused ([home.templ](references/home.templ) shows both).
- **Tailwind CSS v4**: CSS-first config compiled by the standalone `tailwindcss` binary from mise; no Node toolchain.
- **JavaScript**: `esbuild` bundles `assets/js/app.js` into `static/js/dist.js`; skip the bundler while the client side is a couple of inline snippets, and record that decision in `AGENTS.md`.
- **`assets/` vs `static/`**: authored sources live in `assets/`; only build output and vendored libraries live in `static/`, which `server.go` embeds whole — a source left in `static/` ships in the binary.
- **Self-hosted assets**: HTMX, Alpine, CSS, and JS are served from embedded `/static/` with content-hash cache busting; one binary, no CDN, no runtime fetch.
- **Production HTTP**: explicit `http.Server` timeouts; `SetupOTel` in `main` and `NewAppHandler` wrapping the router in `otelhttp` (see §1).

## 5. CLI & TUI

- **Framework**: `urfave/cli/v3` ([cli.go](references/cli.go)); flags, streams, exit codes, and completions follow [cli-contracts](../cli-contracts/SKILL.md).
- **Dual CLI/library**: domain logic and types in the root `Package`, command wiring in `cmd/<slug>/main.go`.
- **TUI**: Bubble Tea and the Charm layout tools import from `charm.land/{bubbletea,lipgloss,bubbles}/v2`, not `github.com/charmbracelet`.

## 6. ADK Agents (Go API)

The agent workflow, `agents-cli`, model-pin rationale, and deployment live in [google-adk](../google-adk/SKILL.md); this section keeps the Go API notes behind the [agent.go](references/agent.go) starter.

- **Module**: `google.golang.org/adk/v2` (requires Go 1.26+); read its API from `~/go/pkg/mod`, not memory.
- **Agents and tools**: `llmagent.New(llmagent.Config{...})` (`SubAgents` for trees); `functiontool.New` wraps typed functions with `jsonschema` tags; `tool/geminitool` and `tool/mcptoolset` add built-ins and MCP.
- **Model and auth**: `gemini.NewModel` on the Gemini Enterprise Agent Platform (formerly Vertex AI) with ADC (`GOOGLE_CLOUD_PROJECT`/`GOOGLE_CLOUD_LOCATION` parsed by `caarlos0/env`); the pinned model name lives in the starter.
- **Entry point**: `full.NewLauncher()` owns the CLI (`console` and `web` modes; `web` hosts `webui`, `api`, `a2a`, and Cloud triggers) and parses its own flags, so keep `urfave/cli/v3` for non-agent tools.
- **Streaming and tracing**: consume runs with `for event, err := range …` (`iter.Seq2`); the launcher wires OpenTelemetry itself (`OTEL_EXPORTER_OTLP_ENDPOINT` or `--otel_to_cloud`).

## 7. Configuration

- **Environment-first**: `caarlos0/env/v11` parses env vars into a typed `Config` in the `config` package ([config.go](references/config.go)); `config.Load()` validates on startup and exits 1 through `slog` on failure.
- **Typed environments**: model `development`/`production` as an enum so the literals never appear at call sites.

## 8. Project Layouts

The CLI + library and web + library trees live in [layouts.md](references/layouts.md); every file there maps to a reference in §2.

## 9. Go Idioms

- **Deterministic concurrency tests**: `testing/synctest` virtualizes clocks for goroutine-heavy code.
- **Receiver consistency**: pointer receivers for state, sync fields, or large structs; value receivers for small immutable values; never mix on one type.
- **Zero-value usability**: design structs so the zero value works without a constructor (`sync.Mutex`, `bytes.Buffer`).
- **Pre-allocate**: `make([]T, 0, n)` / `make(map[K]V, n)` when the size is known (`prealloc` lints it).
