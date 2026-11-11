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
1. **Pick one input and output** (e.g., `assets/styles.css` → `static/css/app.css`), exclude generated CSS from formatters, and follow the repo's artifact policy.
1. **Declare explicit `@source` roots** (resolved relative to the stylesheet):
   ```css
   /* Docs: https://tailwindcss.com/docs/detecting-classes-in-source-files */
   @import "tailwindcss" source(none);
   @source "../templates";
   @source "../src";
   ```
1. **Write whole class names**: map conditions to complete literals (`text-red-600`, never `text-{{ color }}-600`); reserve `@source inline(...)` for bounded dynamic sets, and normalize arbitrary utilities with `tailwindcss canonicalize --css assets/styles.css <classes>`.
1. **Wire build and watch tasks** (run `build:css` before `collectstatic` or packaging; use `--watch=always` only under a closed-stdin supervisor and stop task-owned watchers when done):
   ```toml
   # Docs: https://mise.jdx.dev/tasks/
   [tasks."build:css"]
   run = "tailwindcss -i assets/styles.css -o static/css/app.css --minify"

   [tasks."watch:css"]
   run = "tailwindcss -i assets/styles.css -o static/css/app.css --watch"
   ```
1. **Verify source scanning and live CSS**: confirm clean `--minify` output includes classes from nested templates, conditionals, and Python strings (and drops a removed fixture class), then inspect styles and responsive/keyboard states with [chrome-devtools](../../chrome-devtools/SKILL.md).

## Gotchas

- **Explicit roots prevent cwd drift**: `source(none)` + `@source` keeps root and CI invocations identical; register gitignored or external template paths explicitly since Tailwind scans raw text, not Python/Jinja ASTs.
- **Apply brand tokens**: for Fmind apps, import `~/.agents/themes/tailwind/fmind.css` (and `daisyui/fmind.css` when using daisyUI) per [renderers](../../fmind-visuals/references/renderers.md#pinned-files), and follow [fmind-visuals](../../fmind-visuals/SKILL.md) for published assets.

## Documentation

- [Standalone CLI](https://tailwindcss.com/docs/installation/tailwind-cli) · [Source detection](https://tailwindcss.com/docs/detecting-classes-in-source-files)
- Releases: [Tailwind CSS](https://github.com/tailwindlabs/tailwindcss/releases)
