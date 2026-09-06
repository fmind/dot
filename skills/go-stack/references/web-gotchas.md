# Go Web Build Gotchas

- **Tools are not auto-installed**: `run_auto_install = false` means `mise install` must run once after `mise trust`.
- **Embedded assets do not hot-reload**: use `mise run watch` (air + Tailwind + esbuild watchers); `.air.toml` excludes `assets/` on purpose so only the watchers' writes into `static/` trigger a rebuild.
- **Commit generated code**: `*_templ.go`, `static/css/dist.css`, and `static/js/dist.js` are committed because `check` compiles `server.go` without running generators; CI's clean-tree check catches staleness.
- **Vendored libraries**: `scripts/vendor.go` pins HTMX and Alpine by URL and sha256 and `install:vendor` skips when present; bump a version by editing URL and hash together, never through npm.
- **Alpine load order**: [layout.templ](references/layout.templ) loads `dist.js` before `alpine.min.js` because `Alpine.data()` registrations must exist at `alpine:init`; reversing the tags fails silently.
- **`ko` is per project**: `build:image` needs `go get -tool github.com/google/ko` per [containerize](../containerize/SKILL.md).
- **Transitive vulnerabilities**: `govulncheck` flags modules you never imported (e.g. `grpc` via OTel/ADK); fix with `go get -u <module> && go mod tidy`, not a `require` pin — fresh ADK agents hit this on the first `check`.
