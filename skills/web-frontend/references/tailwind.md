# Standalone Tailwind for Python Web Applications

Compile Tailwind via the standalone `tailwindcss` binary in `mise.toml` without adding a Node dependency graph ([web-frontend](../SKILL.md) owns CSS authoring; Django/Litestar owns static serving).

## Workflow

1. **Pin standalone `tailwindcss` in the project** (not installed globally; pick glibc on Linux since musl needs `/lib/ld-musl-*`):
   ```toml
   # Docs: https://mise.jdx.dev/dev-tools/backends/github.html
   [tools."github:tailwindlabs/tailwindcss"]
   version = "<exact>"

   [tools."github:tailwindlabs/tailwindcss".platforms]
   linux-arm64 = { asset_pattern = "tailwindcss-linux-arm64" }
   linux-x64 = { asset_pattern = "tailwindcss-linux-x64" }
   macos-arm64 = { asset_pattern = "tailwindcss-macos-arm64" }
   ```
1. **Pick one input and output** (e.g., `assets/styles.css` -> `src/<package>/static/css/app.css` so wheels and runtime containers bundle compiled assets without extra root copies), vendor static JS locally (e.g., download version-pinned `htmx.min.js` + SHA-256 verification into `static/vendor/`, never runtime CDNs), exclude generated CSS from formatters, and gitignore compiled outputs only if `build` always regenerates them.
1. **Declare explicit `@source` roots** (resolved relative to the stylesheet):
   ```css
   /* Docs: https://tailwindcss.com/docs/detecting-classes-in-source-files */
   @import "tailwindcss" source(none);
   @source "../src/<package>/templates";
   @source "../src/<package>";
   ```
1. **Write whole class names**: map conditions to complete literals (`text-red-600`, never `text-{{ color }}-600`); reserve `@source inline(...)` for bounded dynamic sets, and normalize arbitrary utilities with `tailwindcss canonicalize --css assets/styles.css <classes>`.
1. **Wire build and watch tasks** (run `build:css` inside `mise.toml` `build` before `uv build` or Docker COPY; use `--watch=always` only under a closed-stdin supervisor and stop task-owned watchers when done):
   ```toml
   # Docs: https://mise.jdx.dev/tasks/
   [tasks."build:css"]
   run = "tailwindcss -i assets/styles.css -o src/<package>/static/css/app.css --minify"

   [tasks."watch:css"]
   run = "tailwindcss -i assets/styles.css -o src/<package>/static/css/app.css --watch"
   ```
   Mount compiled files via `create_static_files_router(path="/static", directories=[...], cache_control=CacheControlHeader(max_age=31_536_000, immutable=True, public=True))` and link via `url_for("static", file_path=...)`.
1. **Verify source scanning and live CSS**: confirm clean `--minify` output includes classes from nested templates, conditionals, and Python strings (and drops a removed fixture class), then inspect styles and responsive/keyboard states with [chrome-devtools](chrome-devtools.md).

## Gotchas

- **Explicit roots prevent cwd drift**: `source(none)` + `@source` keeps root and CI invocations identical; register gitignored or external template paths explicitly since Tailwind scans raw text, not Python/Jinja ASTs.
- **Apply brand tokens**: for Fmind apps, import `~/.agents/themes/tailwind/fmind.css` after `tailwindcss` (and `daisyui/fmind.css` after the plugin with `themes: false`), and follow [diagrams-as-code](../../diagrams-as-code/SKILL.md) for published visual assets.

## Documentation

- [Standalone CLI](https://tailwindcss.com/docs/installation/tailwind-cli) · [Source detection](https://tailwindcss.com/docs/detecting-classes-in-source-files)
- Releases: [Tailwind CSS](https://github.com/tailwindlabs/tailwindcss/releases)
